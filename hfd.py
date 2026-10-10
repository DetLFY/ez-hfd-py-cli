#!/usr/bin/env python3
"""ezhfd-py-cli 入口脚本。

用法::

    python hfd.py            # 交互式下载（默认行为）
    python hfd.py config     # 配置站点 / 路径 / 线程数
    python hfd.py setup      # 仅安装依赖并拉取 hfd.sh
"""

from __future__ import annotations

import sys

from hfd_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
