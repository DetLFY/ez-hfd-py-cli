"""配置管理：读取 / 写入 ``~/.ezhfd/config.json``。

应用数据目录 ``~/.ezhfd`` 统一存放 ``config.json`` 与 ``hfd.sh``，
默认下载路径亦位于该目录之下。

固化的配置项：

* ``site``          —— 下载站点（默认 Hugging Face 镜像站 ``https://hf-mirror.com``）
* ``download_path`` —— 下载路径（默认 ``~/.ezhfd/models``）
* ``threads``       —— 下载线程数（默认 4）
* ``concurrency``   —— 并发下载数（默认 5，高级项）
* ``tool``          —— 下载工具（默认 ``aria2c``，高级项）
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# 应用数据目录：统一存放 config.json 与 hfd.sh
EZHFD_HOME: Path = Path("~/.ezhfd").expanduser()
CONFIG_FILE: Path = EZHFD_HOME / "config.json"

DEFAULT_SITE = "https://hf-mirror.com"
# 旧版本默认下载站点，读取配置时自动迁移到 DEFAULT_SITE
LEGACY_SITE = "https://huggingface.co"
DEFAULT_DOWNLOAD_PATH = "~/.ezhfd/models"
# 旧版本默认下载路径，读取配置时自动迁移到 DEFAULT_DOWNLOAD_PATH
LEGACY_DOWNLOAD_PATH = "~/.ezhfd"
DEFAULT_THREADS = 4
DEFAULT_CONCURRENCY = 5
DEFAULT_TOOL = "aria2c"


def ensure_home_dir() -> Path:
    """确保应用数据目录存在，并返回该目录。"""
    EZHFD_HOME.mkdir(parents=True, exist_ok=True)
    return EZHFD_HOME


def _as_int(value: Any, default: int) -> int:
    """尽量把 value 转成 int，失败时返回 default。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_site(value: Any) -> str:
    """规范化下载站点，并把旧版默认站点迁移为新默认站点。

    * 为空时回落到 ``DEFAULT_SITE``；
    * 旧版默认值 ``https://huggingface.co`` 迁移为 ``https://hf-mirror.com``。
    """
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return DEFAULT_SITE
    if raw == LEGACY_SITE:
        return DEFAULT_SITE
    return raw


def _normalize_download_path(value: Any) -> str:
    """规范化下载路径，并把旧版默认路径迁移为新默认路径。

    * 为空时回落到 ``DEFAULT_DOWNLOAD_PATH``；
    * 旧版默认值 ``~/.ezhfd``（含其展开形式）迁移为 ``~/.ezhfd/models``。
    """
    raw = str(value or "").strip()
    if not raw:
        return DEFAULT_DOWNLOAD_PATH
    try:
        if Path(raw).expanduser() == EZHFD_HOME:
            return DEFAULT_DOWNLOAD_PATH
    except (OSError, RuntimeError):
        pass
    return raw


@dataclass
class Config:
    """固化的下载配置。"""

    site: str = DEFAULT_SITE
    download_path: str = DEFAULT_DOWNLOAD_PATH
    threads: int = DEFAULT_THREADS
    concurrency: int = DEFAULT_CONCURRENCY
    tool: str = DEFAULT_TOOL

    # ------------------------------------------------------------------ #
    # 序列化
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        return cls(
            site=_normalize_site(data.get("site")),
            download_path=_normalize_download_path(data.get("download_path")),
            threads=_as_int(data.get("threads"), DEFAULT_THREADS),
            concurrency=_as_int(data.get("concurrency"), DEFAULT_CONCURRENCY),
            tool=str(data.get("tool") or DEFAULT_TOOL),
        )

    # ------------------------------------------------------------------ #
    # 路径
    # ------------------------------------------------------------------ #
    @property
    def resolved_download_path(self) -> Path:
        """把 ``~`` 展开后的下载根目录。"""
        return Path(self.download_path).expanduser()

    def local_dir_for(self, repo_id: str) -> Path:
        """下载路径拼接仓库名，例如 ``~/.ezhfd/models/org/repo``。"""
        return self.resolved_download_path / repo_id

    def is_valid(self) -> bool:
        """下载路径是必填项，为空视为无效配置。"""
        return bool(self.download_path and self.download_path.strip())


def load_config() -> Optional[Config]:
    """读取配置。

    文件不存在、JSON 非法、或缺少必需的下载路径时返回 ``None``，
    调用方应据此触发配置向导。
    """
    if not CONFIG_FILE.exists():
        return None
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    config = Config.from_dict(raw)
    return config if config.is_valid() else None


def save_config(config: Config) -> Path:
    """把配置写入 ``~/.ezhfd/config.json``，返回文件路径。"""
    ensure_home_dir()
    CONFIG_FILE.write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return CONFIG_FILE
