"""命令行交互：配置向导、下载流程与子命令入口。"""

from __future__ import annotations

import argparse
import os
import re
from typing import Dict, List, Optional, Sequence

from . import __version__
from .config import CONFIG_FILE, Config, load_config, save_config
from .downloader import run_download
from .hfd_manager import ensure_hfd_script
from .installer import ensure_dependencies
from .repo import RepoError, fetch_repo_files


# --------------------------------------------------------------------------- #
# 通用输入辅助
# --------------------------------------------------------------------------- #
def _format_size(num: float) -> str:
    """把字节数格式化为人类可读的字符串（十进制单位）。"""
    value = float(num or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1000:
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.2f}{unit}"
        value /= 1000
    return f"{value:.2f}PB"


def _prompt(label: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
    """单行输入；直接回车使用默认值。"""
    suffix = f" [{default}]" if default not in (None, "") else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default not in (None, ""):
            return str(default)
        if allow_empty:
            return ""
        print("该项不能为空，请重新输入。")


def _prompt_int(label: str, default: int, low: Optional[int] = None, high: Optional[int] = None) -> int:
    """整数输入；直接回车使用默认值。"""
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            value = int(raw)
            if (low is None or value >= low) and (high is None or value <= high):
                return value
        if low is not None and high is not None:
            print(f"请输入 {low}-{high} 之间的整数，或直接回车使用默认值。")
        else:
            print("请输入有效的整数，或直接回车使用默认值。")


# --------------------------------------------------------------------------- #
# 配置向导
# --------------------------------------------------------------------------- #
def run_config_wizard(base: Optional[Config] = None) -> Config:
    """交互式配置向导：回车使用默认值，输入则自定义。"""
    base = base or Config()
    print("=== hfd 配置向导（直接回车使用默认值） ===")
    site = _prompt("下载站点", base.site)
    download_path = _prompt("下载路径", base.download_path)
    threads = _prompt_int("下载线程数 (1-10)", base.threads, 1, 10)

    config = Config(
        site=site.strip(),
        download_path=download_path.strip(),
        threads=threads,
        concurrency=base.concurrency,
        tool=base.tool,
    )
    save_config(config)
    print(f"✓ 配置已保存到 {CONFIG_FILE}\n")
    return config


# --------------------------------------------------------------------------- #
# 文件列表展示与选择
# --------------------------------------------------------------------------- #
def _print_file_table(files: Sequence[Dict[str, object]]) -> None:
    index_width = len(str(len(files)))
    print(f"\n{'序号'.rjust(index_width)}  {'大小':>10}  文件名")
    print("-" * 64)
    for index, item in enumerate(files, start=1):
        print(f"{str(index).rjust(index_width)}  {_format_size(item['size']):>10}  {item['path']}")
    print("-" * 64)


def _resolve_selection(raw: str, files: Sequence[Dict[str, object]]) -> List[int]:
    """把用户输入解析为 0 基索引列表。

    支持：``all`` / ``*``、序号（``3``）、区间（``2-5``）、
    以及文件名子串（``Qwen3-8B``）。
    """
    raw = raw.strip()
    if raw.lower() in ("all", "*"):
        return list(range(len(files)))

    tokens = [token for token in re.split(r"[,\s]+", raw) if token]
    if not tokens:
        raise ValueError("输入为空")

    picked: set = set()
    for token in tokens:
        if re.fullmatch(r"\d+", token) or re.fullmatch(r"\d+-\d+", token):
            start, _, end = token.partition("-")
            low = int(start)
            high = int(end) if end else low
            if low > high:
                low, high = high, low
            matched = False
            for index in range(low, high + 1):
                if 1 <= index <= len(files):
                    picked.add(index - 1)
                    matched = True
            if not matched:
                raise ValueError(token)
        else:
            needle = token.lower()
            hits = [i for i, item in enumerate(files) if needle in str(item["path"]).lower()]
            if not hits:
                raise ValueError(token)
            picked.update(hits)

    if not picked:
        raise ValueError(raw)
    return sorted(picked)


def _prompt_selection(files: Sequence[Dict[str, object]]) -> List[int]:
    print("提示：可输入序号（如 1,3）、区间（如 2-5）或文件名子串，输入 all 表示全部。")
    while True:
        raw = input("请选择要下载的文件: ").strip()
        try:
            return _resolve_selection(raw, files)
        except ValueError:
            print("输入无效，请重新输入。")


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #
def run_config_command(_: argparse.Namespace) -> int:
    existing = load_config() or Config()
    run_config_wizard(existing)
    return 0


def run_setup_command(args: argparse.Namespace) -> int:
    """只做环境准备：安装依赖 + 拉取 hfd.sh。"""
    ensure_dependencies()
    try:
        ensure_hfd_script(force=args.update_hfd)
    except RuntimeError as exc:
        print(f"! {exc}")
        return 1
    return 0


def run_download_command(args: argparse.Namespace) -> int:
    # 1) 环境准备
    if not args.no_deps:
        ensure_dependencies()
    try:
        script_path = ensure_hfd_script(force=args.update_hfd)
    except RuntimeError as exc:
        print(f"! {exc}")
        return 1

    # 2) 配置：无有效配置时先进入配置向导
    config = load_config()
    if config is None:
        print("\n未检测到有效配置（config.json），请先完成初始化配置。")
        config = run_config_wizard()
    else:
        print(
            f"\n当前配置：站点={config.site}  路径={config.resolved_download_path}  "
            f"线程={config.threads}\n"
        )

    # 3) 仓库名
    repo_id = args.repo or _prompt("请输入完整的仓库名 (例如 ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF)")
    repo_id = repo_id.strip().strip("/")
    if not repo_id:
        print("! 仓库名不能为空。")
        return 1

    # 4) 获取文件列表
    token = os.environ.get("HF_TOKEN") or None
    print(f"正在从 {config.site} 获取仓库文件列表 ...")
    try:
        files = fetch_repo_files(config.site, repo_id, token=token)
    except RepoError as exc:
        print(f"! 获取仓库文件列表失败：{exc}")
        return 1

    if not files:
        print("! 该仓库没有可下载的文件。")
        return 1

    _print_file_table(files)
    total_size = sum(int(item["size"]) for item in files)
    print(f"共 {len(files)} 个文件，合计 {_format_size(total_size)}")

    # 5) 选择文件
    if args.all:
        selected = list(range(len(files)))
    else:
        print("\n请选择下载方式:")
        print("  1) 全部下载")
        print("  2) 选择特定文件下载")
        choice = _prompt("请输入选项", default="1")
        selected = list(range(len(files))) if choice != "2" else _prompt_selection(files)

    selected_paths = [str(files[i]["path"]) for i in selected]
    selected_size = sum(int(files[i]["size"]) for i in selected)
    local_dir = config.local_dir_for(repo_id)

    if not selected_paths:
        print("! 未选择任何文件。")
        return 1

    print(f"\n已选择 {len(selected_paths)} 个文件，合计 {_format_size(selected_size)}")
    print(f"下载目录：{local_dir}")

    # 6) 确认并下载
    if not args.yes:
        confirm = _prompt("确认开始下载？(Y/n)", default="Y").lower()
        if confirm not in ("y", "yes"):
            print("已取消。")
            return 0

    local_dir.mkdir(parents=True, exist_ok=True)

    # 全部下载时不传 --include；部分下载时用精确文件名作为 include 模式。
    include: Optional[List[str]] = None
    if len(selected_paths) != len(files):
        include = selected_paths

    print()
    code = run_download(
        script_path=script_path,
        repo_id=repo_id,
        local_dir=local_dir,
        site=config.site,
        tool=config.tool,
        threads=config.threads,
        concurrency=config.concurrency,
        include=include,
        token=token,
    )

    if code == 0:
        print(f"\n✓ 下载完成：{local_dir}")
    else:
        print(f"\n! 下载进程退出码为 {code}，可重新运行以继续（hfd.sh 支持断点续传）。")
    return code


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ezhfd",
        description="简化 Hugging Face 模型下载（封装 hfd.sh）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python hfd.py config                 # 配置站点/路径/线程\n"
            "  python hfd.py                        # 交互式选择仓库与文件\n"
            "  python hfd.py download --repo org/repo --all -y\n"
            "  python hfd.py setup                  # 仅安装依赖并拉取 hfd.sh\n"
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["download", "config", "setup"],
        default="download",
        help="子命令，默认 download",
    )
    parser.add_argument("--repo", "-r", help="仓库名，例如 org/repo（省略时会提示输入）")
    parser.add_argument("--all", "-a", action="store_true", help="下载全部文件，跳过选择")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过下载前确认")
    parser.add_argument("--no-deps", action="store_true", help="跳过依赖检测与自动安装")
    parser.add_argument("--update-hfd", action="store_true", help="强制重新下载 hfd.sh")
    parser.add_argument("--version", action="version", version=f"ezhfd-py-cli {__version__}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "config":
            return run_config_command(args)
        if args.command == "setup":
            return run_setup_command(args)
        return run_download_command(args)
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
