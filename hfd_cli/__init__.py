"""ezhfd-py-cli: 简化 Hugging Face 模型下载的命令行工具。

本包仅依赖 Python 标准库，通过封装官方 `hfd.sh` 脚本，
提供配置固化、依赖自动安装、仓库文件列表选择等能力。
配置与脚本统一存放于 ``~/.ezhfd`` 目录。
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
