#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#


# Standard library imports
import base64
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from io import BytesIO
from pathlib import Path
import pdfplumber
from PIL import Image, ImageDraw, ImageFont

# Local imports
from api.constants import IMG_BASE64_PREFIX
from api.db import FileType

LOCK_KEY_pdfplumber = "global_shared_lock_pdfplumber"
if LOCK_KEY_pdfplumber not in sys.modules:
    sys.modules[LOCK_KEY_pdfplumber] = threading.Lock()


def _placeholder_thumbnail(ext: str):
    # create a small, deterministic placeholder thumbnail with the file extension
    width = 200
    height = 300
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    text = ext.upper()[:4] if ext else "FILE"
    try:
        font_path = Path(__file__).parent / "SourceHanSerifCN-Bold.ttf"
        font = ImageFont.truetype(str(font_path), max(10, min(12, width // 15)))
    except Exception:
        font = None
    _, _, tw, th = draw.textbbox((0, 0), text=text, font=font)
    # tw, th = draw.textsize(text, font=font)
    draw.text(((100 - tw) / 2, (100 - th) / 2), text, fill=(60, 90, 140), font=font)
    buffered = BytesIO()
    img.save(buffered, format="png")
    return buffered.getvalue()


def filename_type(filename):
    filename = filename.lower()
    if re.match(r".*\.pdf$", filename):
        return FileType.PDF.value

    if re.match(r".*\.(msg|eml|doc|docx|ppt|pptx|yml|xml|htm|json|jsonl|ldjson|csv|txt|ini|xls|xlsx|wps|rtf|hlp|pages|numbers|key|md|py|js|java|c|cpp|h|php|go|ts|sh|cs|kt|html|sql)$", filename):
        return FileType.DOC.value

    if re.match(r".*\.(wav|flac|ape|alac|wavpack|wv|mp3|aac|ogg|vorbis|opus)$", filename):
        return FileType.AURAL.value

    if re.match(
        r".*\.(jpg|jpeg|png|tif|gif|pcx|tga|exif|fpx|svg|psd|cdr|pcd|dxf|ufo|eps|ai|raw|WMF|webp|avif|apng|icon|ico|mpg|mpeg|avi|rm|rmvb|mov|wmv|asf|dat|asx|wvx|mpe|mpa|mp4|avi|mkv)$", filename
    ):
        return FileType.VISUAL.value

    return FileType.OTHER.value


def thumbnail_img(filename, blob):
    """
    MySQL LongText max length is 65535
    """
    filename = filename.lower()
    if re.match(r".*\.pdf$", filename):
        with sys.modules[LOCK_KEY_pdfplumber]:
            pdf = pdfplumber.open(BytesIO(blob))

            buffered = BytesIO()
            resolution = 32
            img = None
            for _ in range(10):
                # https://github.com/jsvine/pdfplumber?tab=readme-ov-file#creating-a-pageimage-with-to_image
                pdf.pages[0].to_image(resolution=resolution).annotated.save(buffered, format="png")
                img = buffered.getvalue()
                if len(img) >= 64000 and resolution >= 2:
                    resolution = resolution / 2
                    buffered = BytesIO()
                else:
                    break
        pdf.close()
        return img

    elif re.match(r".*\.(jpg|jpeg|png|tif|gif|icon|ico|webp)$", filename):
        image = Image.open(BytesIO(blob))
        image.thumbnail((200, 300))
        buffered = BytesIO()
        image.save(buffered, format="png")
        return buffered.getvalue()

    elif re.match(r".*\.(ppt|pptx)$", filename):
        import aspose.pydrawing as drawing
        import aspose.slides as slides

        try:
            with slides.Presentation(BytesIO(blob)) as presentation:
                buffered = BytesIO()
                scale = 0.03
                img = None
                for _ in range(10):
                    # https://reference.aspose.com/slides/python-net/aspose.slides/slide/get_thumbnail/#float-float
                    presentation.slides[0].get_thumbnail(scale, scale).save(buffered, drawing.imaging.ImageFormat.png)
                    img = buffered.getvalue()
                    if len(img) >= 64000:
                        scale = scale / 2.0
                        buffered = BytesIO()
                    else:
                        break
                return img
        except Exception:
            pass

    elif re.match(r".*\.(txt|md)", filename):
        try:
            width = 200
            height = 300
            img = Image.new("RGB", (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            font_path = Path(__file__).parent / "SourceHanSerifCN-Bold.ttf"
            font = ImageFont.truetype(str(font_path), max(10, min(12, width // 15)))

            text_content = blob.decode("utf-8", errors="replace")[:2000]
            text_content = text_content.replace("\r\n", "\n").replace("\r", "\n")

            # file_type_label = "文本文件" if file_type == ".txt" else "Markdown文件"
            # draw.text((10, 10), file_type_label, font=font, fill=(0, 0, 0))
            draw.line([(10, 30), (width - 10, 30)], fill=(200, 200, 200), width=1)

            y_position = 40
            font_size = max(10, min(12, width // 15))
            chars_per_line = max(1, width // (font_size // 2 + 1))
            max_lines = (height - 50) // (font_size + 2)

            lines = []
            for paragraph in text_content.split("\n"):
                if not paragraph:
                    lines.append("")
                    continue
                for i in range(0, len(paragraph), chars_per_line):
                    lines.append(paragraph[i : i + chars_per_line])

            for i, line in enumerate(lines[:max_lines]):
                draw.text((10, y_position), line, font=font, fill=(0, 0, 0))
                y_position += font_size + 2

            if len(lines) > max_lines:
                draw.text((10, height - 20), "...", font=font, fill=(0, 0, 0))

            buffered = BytesIO()
            img.save(buffered, format="png")
            return buffered.getvalue()
        except Exception:
            pass
    else:
        # create a small, deterministic placeholder thumbnail with the file extension
        width = 200
        height = 300
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        text = filename.upper()[:4] if filename else "FILE"
        try:
            font_path = Path(__file__).parent / "SourceHanSerifCN-Bold.ttf"
            font = ImageFont.truetype(str(font_path), 40)
        except Exception:
            font = None
        _, _, tw, th = draw.textbbox((0, 0), text=text, font=font)

        # tw, th = draw.textsize(text, font=font)
        draw.text(((64 - 40) / 2, (64 - 40) / 2), text, fill=(60, 90, 140), font=font)
        buffered = BytesIO()
        img.save(buffered, format="png")
        return buffered.getvalue()
    return None


def thumbnail(filename, blob):
    img = thumbnail_img(filename, blob)
    if img is not None:
        return IMG_BASE64_PREFIX + base64.b64encode(img).decode("utf-8")
    else:
        return ""


def repair_pdf_with_ghostscript(input_bytes):
    if shutil.which("gs") is None:
        return input_bytes

    with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_in, tempfile.NamedTemporaryFile(suffix=".pdf") as temp_out:
        temp_in.write(input_bytes)
        temp_in.flush()

        cmd = [
            "gs",
            "-o",
            temp_out.name,
            "-sDEVICE=pdfwrite",
            "-dPDFSETTINGS=/prepress",
            temp_in.name,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return input_bytes
        except Exception:
            return input_bytes

        temp_out.seek(0)
        repaired_bytes = temp_out.read()

    return repaired_bytes


def read_potential_broken_pdf(blob):
    def try_open(blob):
        try:
            with pdfplumber.open(BytesIO(blob)) as pdf:
                if pdf.pages:
                    return True
        except Exception:
            return False
        return False

    if try_open(blob):
        return blob

    repaired = repair_pdf_with_ghostscript(blob)
    if try_open(repaired):
        return repaired

    return blob
