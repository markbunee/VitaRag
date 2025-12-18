# config.py
""" 配置文件，支持动态加载系统常量和API配置信息 """
import logging
import os
import time
import json
from typing import Dict, Any, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
# 日志配置
LOG_FORMAT = "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(format=LOG_FORMAT)

def log_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logging.info(f"{func.__name__} executed in {elapsed_time:.6f} seconds")
        return result
    return wrapper

class ModelConfig(BaseSettings):
    model_name: str
    api_base_url: str
    api_key: str
    max_length: int
    max_tokens: Optional[int] = None
    temperature: float = 0.8
    top_p: float = 1.0

from typing import Dict, Any, List, Optional, ClassVar

class AppConfig(BaseSettings):
    # 路径配置
    LOG_PATH: str = Field(default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs"))
    TEMP_DIR_PATH: str = "temp/upload_files"

    # OCR配置
    OCR_ENABLED: bool = True

    # JWT配置
    SECRET_KEY: str = "zhisuan-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3

    # 用户配置
    USERS: Dict[str, Dict[str, Any]] = {
        "admin": {
            "username": "admin",
            # 这里的是 hashed_password 而不是 password
            "hashed_password": "$2b$12$kZ3sG4o7rX2fsem9iq3hR.xC0OLxJR7HbR.hQxLrxJ8r89hydwGGe",
            "email": "admin@example.com",
            "full_name": "Admin User",
            "disabled": False,
            "is_admin": True,
            "scopes": ["admin"]
        },
    }

    # Token限制
    MAX_INPUT_TOKENS: int = 14000
    MAX_PROMPT_TOKENS: int = 28000

    # 字符限制
    MAX_DOC_CONTENT_LENGTH: int = 40000

    # # 知识库配置
    # KNOWLEDGE_BASE_URL: str = "http://uf-web:9997"
    # TOKEN: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MjQ2MjM3NDcwOH0.CsnK7wAQPZrTDsgmu-Ls5fYqKUDC-_e8k65FXG2PvDc"
    # DIFY_compatible: bool = False
    # @property
    # def FILE_EXTRACTION_API(self) -> str:
    #     return f"{self.KNOWLEDGE_BASE_URL}/api/v0/read/deep-multi-analyze"

    # @property
    # def KNOWLEDGE_BASE_API(self) -> str:
    #     return f"{self.KNOWLEDGE_BASE_URL}/api/v0/search/multi"

    @property
    def FILE_EXTRACTION_BODY(self) -> Dict[str, str]:
        return {
            "tables": "True",
            "start_page": "0",
            "end_page": "50",
            "force_ocr": str(self.OCR_ENABLED)
        }

    # 知识库检索参数
    DEFAULT_TOP_K: int = 40
    DEFAULT_TOP_N: int = 3
    DEFAULT_KEY_WEIGHT: float = 0.8
    RERANK_MODEL: str = "bge-reranker-v2-m3"
    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT: str = """"""

    # 文件上传限制
    allowed_extensions: List[str] = ['txt', 'md', 'html', 'pdf', 'docx', 'xlsx', 'xls', 'csv', 'rdf', 'pptx', 'json','.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']
    max_size: int = 10 * 1024 * 1024

    # 模型配置
    AGENT_LLM_MODELS: List[str] = ["qwen-14b"]
    COT_LLM_MODELS: List[str] = ["deepseek-r1-32b"]
    LLM_MODEL_API: Dict[str, Dict[str, Any]] = {
        "qwen-14b": {
            "model_name": "qwen-14b",
            "api_base_url": "http://36.141.21.178:1035/v1",
            "api_key": "token-abc123",
            "max_length": 32000,
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 1,
            "qwords":"",
        },
        "deepseek-r1-32b": {
            "model_name": "deepseek-r1-32b",
            "api_base_url": "http://36.141.20.215:1025/v1",
            "api_key": "token-abc123",
            "max_length": 128000,
            "max_tokens": 4096,
            "temperature": 0.6,
            "top_p": 0.9,
            "qwords":"\n你需要先思考再输出",
            "reasoning_nonstandard": True # 非标准思维链返回，标准的思维链返回则不填该值即可
        },
        "Qwen3-32B": {
            "model_name": "Qwen3-32B",
            "api_base_url": "http://36.141.20.215:1035/v1",
            "api_key": "token-abc123",
            "max_length": 22000,
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 1,
            "qwords": "/no_think"
        }
    }

    OA_EXPENSE_API_URL: ClassVar[str] = "http://192.168.30.207:8111/api/expense/ai-records"
    OA_EXPENSE_API_DEFAULTS: ClassVar[Dict[str, Any]] = {
        "pageNum": 1,
        "pageSize": 10,
        "force_ocr": False
    }

    # 天气API配置
    BAIDU_WEATHER_API_URL: str = "https://api.map.baidu.com/weather/v1/"
    BAIDU_WEATHER_API_KEY: str = "YOUR_BAIDU_API_KEY_PLACEHOLDER"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "APP_"
    }

    def load_from_json(self, json_file_path: str) -> None:
        """从JSON文件加载配置"""
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            logger.info(f"Configuration loaded from {json_file_path}")

    def reload(self) -> 'AppConfig':
        """重新加载配置"""
        # 从环境变量重新加载
        for field in self.__fields__:
            env_var = f"APP_{field.upper()}"
            if env_var in os.environ:
                try:
                    value = os.environ[env_var]
                    # 尝试转换为正确的类型
                    field_type = self.__fields__[field].type_
                    if field_type == bool:
                        value = value.lower() in ('true', '1', 't', 'yes')
                    elif field_type == int:
                        value = int(value)
                    elif field_type == float:
                        value = float(value)
                    elif field_type in (dict, list):
                        value = json.loads(value)
                    setattr(self, field, value)
                except Exception as e:
                    logger.error(f"Error loading {field} from environment: {e}")

        # 如果存在配置文件，也重新加载
        config_path = os.environ.get("APP_CONFIG_PATH", "config.json")
        if os.path.exists(config_path):
            self.load_from_json(config_path)
        logger.info("Configuration reloaded")
        return self


# 创建配置单例
config = AppConfig()

# 创建日志目录
if not os.path.exists(config.LOG_PATH):
    os.mkdir(config.LOG_PATH)

# 导出单例，方便其他模块导入
def get_config():
    return config
