"""全局配置：从 backend/.env 读取环境变量。"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # 大模型（DeepSeek / 任意 OpenAI 兼容接口）
    deepseek_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # MCP 工具服务地址
    mcp_url: str = "http://127.0.0.1:8001/sse"

    # SMTP（可选，用于真实发送报告邮件）
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_to: str = ""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
