"""``hfd.sh`` 脚本管理：检测本地脚本，不存在时从镜像下载。"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from .config import EZHFD_HOME, ensure_home_dir

HFD_SCRIPT_URL = "https://hf-mirror.com/hfd/hfd.sh"
HFD_SCRIPT: Path = EZHFD_HOME / "hfd.sh"
_USER_AGENT = "ezhfd-py-cli/1.0"


def hfd_script_path() -> Path:
    """本地 ``hfd.sh`` 的路径。"""
    return HFD_SCRIPT


def ensure_hfd_script(force: bool = False) -> Path:
    """确保本地存在可用的 ``hfd.sh``。

    * 已存在且非空（且 ``force`` 为 False）时直接复用；
    * 否则从 ``HFD_SCRIPT_URL`` 下载并赋予可执行权限。
    """
    if HFD_SCRIPT.exists() and HFD_SCRIPT.stat().st_size > 0 and not force:
        print(f"✓ 已找到 hfd.sh: {HFD_SCRIPT}")
        return HFD_SCRIPT

    print(f"正在从 {HFD_SCRIPT_URL} 下载 hfd.sh ...")
    request = urllib.request.Request(HFD_SCRIPT_URL, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()

    if not content.startswith(b"#!"):
        raise RuntimeError(
            f"下载 hfd.sh 失败：{HFD_SCRIPT_URL} 返回的内容不是有效的 shell 脚本。"
        )

    ensure_home_dir()
    HFD_SCRIPT.write_bytes(content)
    try:
        os.chmod(HFD_SCRIPT, 0o755)
    except OSError:
        pass
    print(f"✓ hfd.sh 已保存到 {HFD_SCRIPT}")
    return HFD_SCRIPT
