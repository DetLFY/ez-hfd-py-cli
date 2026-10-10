"""依赖检测与自动安装。

负责检测并（在可能的情况下）自动安装：

* ``aria2c``  —— hfd.sh 默认使用的下载工具
* ``git-lfs`` —— 大文件支持

自动安装会根据操作系统选择合适的包管理器
（apt / dnf / yum / pacman / zypper / apk / brew / winget）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional, Sequence

# 依赖命令名 -> 包管理器中的包名
_DEP_PACKAGES = {
    "aria2c": "aria2",
    "git-lfs": "git-lfs",
}

DEFAULT_REQUIRED: Sequence[str] = ("aria2c", "git-lfs")


def command_exists(name: str) -> bool:
    """命令是否在 PATH 中可用。"""
    return shutil.which(name) is not None


def missing_dependencies(required: Sequence[str] = DEFAULT_REQUIRED) -> List[str]:
    """返回缺失的依赖命令列表。"""
    return [cmd for cmd in required if not command_exists(cmd)]


# --------------------------------------------------------------------------- #
# 包管理器探测与安装
# --------------------------------------------------------------------------- #
def detect_package_manager() -> Optional[str]:
    """返回可用的包管理器标识，找不到时返回 ``None``。"""
    if sys.platform == "darwin" and command_exists("brew"):
        return "brew"
    for pm in ("apt", "dnf", "yum", "pacman", "zypper", "apk"):
        if command_exists(pm):
            return pm
    if command_exists("brew"):
        return "brew"
    return None


def _privilege_prefix(package_manager: str) -> Optional[List[str]]:
    """返回提权命令前缀。

    ``[]`` 表示无需提权，``["sudo"]`` 表示需要 sudo，
    ``None`` 表示既非 root 又没有 sudo，无法自动安装。
    """
    if package_manager == "brew":
        return []
    if not hasattr(os, "geteuid") or os.geteuid() == 0:
        return []
    if command_exists("sudo"):
        return ["sudo"]
    return None


def _install_commands(package_manager: str, packages: Sequence[str]) -> List[List[str]]:
    """把包列表翻译成具体的一条或多条安装命令。"""
    pkgs = list(packages)
    if package_manager == "apt":
        return [["apt-get", "update"], ["apt-get", "install", "-y", *pkgs]]
    if package_manager in ("dnf", "yum"):
        return [[package_manager, "install", "-y", *pkgs]]
    if package_manager == "pacman":
        return [["pacman", "-Sy", "--noconfirm", *pkgs]]
    if package_manager == "zypper":
        return [["zypper", "install", "-y", *pkgs]]
    if package_manager == "apk":
        return [["apk", "add", *pkgs]]
    if package_manager == "brew":
        return [["brew", "install", *pkgs]]
    return []


def _run(command: Sequence[str]) -> int:
    print(f"  $ {' '.join(command)}")
    try:
        return subprocess.run(list(command)).returncode
    except FileNotFoundError:
        return 127


def _install_windows(packages: Sequence[str]) -> bool:
    if not command_exists("winget"):
        print("! Windows 上未找到 winget，请手动安装：" + ", ".join(packages))
        print("  aria2:  https://github.com/aria2/aria2/releases")
        print("  git-lfs: https://git-lfs.com/")
        return False
    winget_names = {"aria2": "aria2.aria2", "git-lfs": "GitHub.GitLFS"}
    ok = True
    for pkg in packages:
        code = _run(
            [
                "winget",
                "install",
                "--accept-source-agreements",
                "--accept-package-agreements",
                winget_names.get(pkg, pkg),
            ]
        )
        ok = ok and code == 0
    return ok


def install_packages(packages: Sequence[str]) -> bool:
    """使用系统包管理器安装指定的软件包，返回是否全部成功。"""
    packages = [p for p in packages if p]
    if not packages:
        return True

    if sys.platform.startswith("win"):
        return _install_windows(packages)

    package_manager = detect_package_manager()
    if package_manager is None:
        print("! 未检测到受支持的包管理器，无法自动安装。")
        print("  支持的包管理器：apt / dnf / yum / pacman / zypper / apk / brew")
        return False

    prefix = _privilege_prefix(package_manager)
    if prefix is None:
        print("! 需要管理员权限，但当前环境没有 sudo，请手动安装：" + ", ".join(packages))
        return False

    commands = _install_commands(package_manager, packages)
    if not commands:
        return False

    for command in commands:
        if _run(prefix + command) != 0:
            print("! 安装命令执行失败。")
            return False
    return True


def ensure_dependencies(required: Sequence[str] = DEFAULT_REQUIRED) -> bool:
    """确保依赖已安装：缺失时尝试自动安装。

    返回 ``True`` 表示所有依赖最终可用，``False`` 表示仍有缺失。
    """
    missing = missing_dependencies(required)
    if not missing:
        print("✓ 依赖检查通过：aria2 与 git-lfs 均已安装。")
        return True

    print(f"! 检测到缺失依赖：{', '.join(missing)}，尝试自动安装 ...")
    packages: List[str] = []
    for cmd in missing:
        pkg = _DEP_PACKAGES.get(cmd, cmd)
        if pkg not in packages:
            packages.append(pkg)

    install_packages(packages)

    still_missing = missing_dependencies(required)
    if not still_missing:
        print("✓ 依赖安装完成。")
        return True

    print("! 以下依赖仍未安装：" + ", ".join(still_missing))
    print("  请参考 README「手动安装依赖」一节处理后再试。")
    return False
