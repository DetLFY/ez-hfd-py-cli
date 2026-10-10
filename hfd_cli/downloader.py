"""调用 ``hfd.sh`` 执行下载。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence


def find_bash() -> Optional[str]:
    """定位 bash 可执行文件。"""
    return shutil.which("bash")


def build_command(
    script_path: Path,
    repo_id: str,
    local_dir: Path,
    tool: str,
    threads: int,
    concurrency: int,
    include: Optional[Sequence[str]] = None,
    revision: Optional[str] = None,
    is_dataset: bool = False,
) -> List[str]:
    """构造等价的 hfd.sh 命令行。"""
    bash = find_bash() or "bash"
    command = [
        bash,
        str(script_path),
        repo_id,
        "--tool",
        tool,
        "-x",
        str(threads),
        "-j",
        str(concurrency),
        "--local-dir",
        str(local_dir),
    ]
    if is_dataset:
        command.append("--dataset")
    if revision:
        command += ["--revision", revision]
    if include:
        command.append("--include")
        command.extend(include)
    return command


def run_download(
    script_path: Path,
    repo_id: str,
    local_dir: Path,
    site: str,
    tool: str,
    threads: int,
    concurrency: int,
    include: Optional[Sequence[str]] = None,
    revision: Optional[str] = None,
    is_dataset: bool = False,
    token: Optional[str] = None,
) -> int:
    """执行下载，返回子进程退出码。"""
    command = build_command(
        script_path=script_path,
        repo_id=repo_id,
        local_dir=local_dir,
        tool=tool,
        threads=threads,
        concurrency=concurrency,
        include=include,
        revision=revision,
        is_dataset=is_dataset,
    )

    env = os.environ.copy()
    env["HF_ENDPOINT"] = site
    if token:
        env.setdefault("HF_TOKEN", token)

    print(f"下载站点 : {site}")
    print(f"本地目录 : {local_dir}")
    print(f"线程/并发: -x {threads} -j {concurrency}")
    print(f"执行命令 : {' '.join(command)}\n")

    try:
        return subprocess.run(command, env=env).returncode
    except FileNotFoundError:
        print("! 未找到 bash，请先安装 bash（Windows 用户可使用 Git Bash 或 WSL）。")
        return 1
