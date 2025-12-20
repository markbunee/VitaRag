from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import os

from common.constants import LLMType
from api.db.services.llm_service import LLMBundle
from common.connection_utils import timeout
from rag.app.picture import vision_llm_chunk as picture_vision_llm_chunk
from rag.prompts.generator import vision_llm_figure_describe_prompt
try:
    from rag.app.cell_classifier import cell_classifier
except ImportError:
    cell_classifier = None


# =========================
# Utils
# =========================

def vision_figure_parser_figure_data_wrapper(figures_data_without_positions):
    return [
        (
            (figure_data[1], [figure_data[0]]),
            [(0, 0, 0, 0, 0)],
        )
        for figure_data in figures_data_without_positions
        if isinstance(figure_data, (list, tuple))
        and len(figure_data) >= 2
        and isinstance(figure_data[1], Image.Image)
    ]


def vision_figure_parser_docx_wrapper(sections, tbls, callback=None, **kwargs):
    vision_model = None
    try:
        vision_model = LLMBundle(kwargs["tenant_id"], LLMType.IMAGE2TEXT)
        callback(0.7, "Visual model detected. Attempting to enhance figure extraction...")
    except Exception:
        vision_model = None

    if vision_model:
        figures_data = vision_figure_parser_figure_data_wrapper(sections)
        try:
            parser = VisionFigureParser(
                vision_model=vision_model,
                figures_data=figures_data,
            )
            tbls.extend(parser(callback=callback))
        except Exception as e:
            callback(0.8, f"Visual model error: {e}")

    return tbls


def vision_figure_parser_pdf_wrapper(tbls, callback=None, **kwargs):
    vision_model = None
    try:
        vision_model = LLMBundle(kwargs["tenant_id"], LLMType.IMAGE2TEXT)
        callback(0.7, "Visual model detected. Attempting to enhance figure extraction...")
    except Exception:
        vision_model = None

    # Check classifier existence
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    has_classifier = os.path.exists(
        os.path.join(project_root, "rag", "res", "cell_model.pth")
    )

    if not vision_model and not has_classifier:
        return tbls

    def is_figure_item(item):
        try:
            return (
                isinstance(item, (list, tuple))
                and isinstance(item[0], (list, tuple))
                and isinstance(item[0][0], Image.Image)
                and isinstance(item[0][1], list)
            )
        except Exception:
            return False

    figures_data = [item for item in tbls if is_figure_item(item)]

    try:
        parser = VisionFigureParser(
            vision_model=vision_model,
            figures_data=figures_data,
        )
        boosted = parser(callback=callback)
        tbls = [item for item in tbls if not is_figure_item(item)]
        tbls.extend(boosted)
    except Exception as e:
        callback(0.8, f"Figure processing error: {e}")

    return tbls


# =========================
# Executor（本机安全）
# =========================

shared_executor = ThreadPoolExecutor(max_workers=2)


# =========================
# Core Parser
# =========================

class VisionFigureParser:
    _classifier = None  # 单例

    def __init__(self, vision_model, figures_data, *args, **kwargs):
        self.vision_model = vision_model
        self._extract_figures_info(figures_data)

        assert len(self.figures) == len(self.descriptions)
        assert not self.positions or len(self.figures) == len(self.positions)

    def _extract_figures_info(self, figures_data):
        self.figures = []
        self.descriptions = []
        self.positions = []

        for item in figures_data:
            if (
                len(item) == 2
                and isinstance(item[0], tuple)
                and isinstance(item[1], list)
            ):
                img, desc = item[0]
                self.figures.append(img)
                self.descriptions.append(list(desc))  # 始终 list
                if item[1]:
                    self.positions.append(item[1])
            else:
                img, desc = item
                self.figures.append(img)
                self.descriptions.append(list(desc))

    def _assemble(self):
        assembled = []
        has_pos = len(self.positions) == len(self.figures)

        for i, fig in enumerate(self.figures):
            if has_pos:
                assembled.append(((fig, self.descriptions[i]), self.positions[i]))
            else:
                assembled.append(((fig, self.descriptions[i]),))
        return assembled

    def __call__(self, **kwargs):
        callback = kwargs.get("callback", lambda p, m: None)

        # ---- Init classifier once ----
        if VisionFigureParser._classifier is None:
            try:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                model_path = os.path.join(project_root, "rag", "res", "cell_model.pth")
                if os.path.exists(model_path) and cell_classifier:
                    cell_classifier.initialize(model_path)
                    VisionFigureParser._classifier = cell_classifier
            except Exception as e:
                callback(0.8, f"Cell classifier init failed: {e}")

        classifier = VisionFigureParser._classifier

        @timeout(30, 3)
        def process(idx, img):
            texts = []

            if classifier:
                try:
                    res = classifier.predict(img)
                    if res:
                        texts.append(f"[AI Detected Cell Type]: {res}")
                except Exception:
                    pass

            if self.vision_model:
                try:
                    vlm = picture_vision_llm_chunk(
                        binary=img,
                        vision_model=self.vision_model,
                        prompt=vision_llm_figure_describe_prompt(),
                        callback=callback,
                    )
                    texts.append(vlm)
                except Exception:
                    pass

            return idx, texts

        futures = [
            shared_executor.submit(process, i, img)
            for i, img in enumerate(self.figures)
        ]

        for fut in as_completed(futures):
            idx, texts = fut.result()
            if texts:
                self.descriptions[idx] = texts + self.descriptions[idx]

        return self._assemble()
