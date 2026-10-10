# ezhfd-py-cli

## 简介

`ezhfd-py-cli` 是一个用于简化 Hugging Face 模型下载的命令行工具。它在官方
[`hfd.sh`](https://hf-mirror.com/hfd/hfd.sh) 脚本之上提供一层封装，用于统一管理运行依赖、
持久化下载配置，并以交互方式选择待下载的仓库文件，从而降低重复输入冗长命令的成本。

## 背景

直接使用 `hfd.sh` 下载模型时，需在每次下载中重复指定仓库名、文件模式、本地目录与并发参数：

```bash
./hfd.sh ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF \
  --include "Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp.gguf" \
  --local-dir /path/to/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF \
  --tool aria2c -x 10
```

`ezhfd-py-cli` 将上述参数固化为配置，并提供文件列表选择能力：

```bash
python hfd.py
# 1. 输入仓库名，例如 ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF
# 2. 从仓库文件列表中选择需要下载的文件
```

## 功能特性

1. **依赖自检与自动安装**：检测 `aria2c` 与 `git-lfs`，缺失时调用系统包管理器自动安装。
2. **脚本自动获取**：本地不存在 `hfd.sh` 时，自动从 `https://hf-mirror.com/hfd/hfd.sh` 下载。
3. **配置持久化**：下载站点、下载路径、线程数等配置写入 `~/.ezhfd/config.json`，跨会话复用。
4. **配置缺失引导**：运行时若不存在有效配置，将自动进入配置向导。
5. **仓库文件选择**：获取仓库完整文件列表后，可整体下载或按序号 / 区间 / 文件名筛选。
6. **路径自动拼接**：下载目录为「配置的下载路径 + 仓库名」，例如 `~/.ezhfd/models/org/repo`。

## 环境要求

| 项目 | 要求 |
| --- | --- |
| Python | 3.8 及以上 |
| 操作系统 | Linux / macOS / Windows（Windows 需 Git Bash 或 WSL 提供 `bash`） |
| 运行依赖 | 仅 Python 标准库，无第三方 Python 依赖 |

系统级依赖 `aria2` 与 `git-lfs` 由工具自动检测与安装，亦可参考
[手动安装依赖](#手动安装依赖)。

## 安装与初始化

```bash
# 1.（可选）仅准备环境：安装系统依赖并获取 hfd.sh
python hfd.py setup

# 2. 配置下载站点 / 下载路径 / 线程数
python hfd.py config

# 3. 交互式下载
python hfd.py
```

首次运行且尚未配置时，工具会自动进入配置流程。

## 配置说明

配置持久化于 `~/.ezhfd/config.json`：

```json
{
  "site": "https://hf-mirror.com",
  "download_path": "~/.ezhfd/models",
  "threads": 4,
  "concurrency": 5,
  "tool": "aria2c"
}
```

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `site` | 下载站点 | `https://hf-mirror.com`（HF 镜像站） |
| `download_path` | 下载根目录 | `~/.ezhfd/models` |
| `threads` | aria2 下载线程数（对应 `-x`，取值 1-10） | `4` |
| `concurrency` | 并发下载数（对应 `-j`，取值 1-10） | `5` |
| `tool` | 下载工具（`aria2c` 或 `wget`） | `aria2c` |

配置向导中，**直接回车使用默认值，输入内容则为自定义值**。向导提示
`site`、`download_path`、`threads` 三项；`concurrency` 与 `tool` 为高级项，
可在 `config.json` 中手动修改。

> 下载站点默认指向镜像站 `https://hf-mirror.com`，亦可改为官方站点 `https://huggingface.co`。

## 使用说明

### 交互式下载（默认行为）

```bash
python hfd.py
```

执行流程：依赖检查 → 配置校验（缺失时进入配置向导）→ 输入仓库名 →
展示文件列表 → 选择「全部下载」或「特定文件」→ 确认 → 下载。

### 指定仓库并整体下载

```bash
python hfd.py download --repo ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF --all -y
```

### 仅执行环境准备

```bash
python hfd.py setup
```

### 命令行参数

| 参数 | 说明 |
| --- | --- |
| `-r, --repo` | 指定仓库名，跳过输入提示 |
| `-a, --all` | 下载全部文件，跳过文件选择 |
| `-y, --yes` | 跳过下载前确认 |
| `--no-deps` | 跳过依赖检测与自动安装 |
| `--update-hfd` | 强制重新下载 `hfd.sh` |
| `--version` | 显示版本信息 |

### 文件选择语法

在「选择特定文件下载」环节，支持以下输入形式：

| 形式 | 示例 |
| --- | --- |
| 序号 | `1,3,5` |
| 区间 | `2-6` |
| 文件名子串 | `Qwen3-8B`、`IQ3_S` |
| 全部 | `all` 或 `*` |
| 混合使用 | `1,3-5,mtp` |

## 私有 / gated 仓库

设置环境变量 `HF_TOKEN` 后可访问需要授权的仓库：

```bash
export HF_TOKEN=hf_xxxxxxxx
python hfd.py
```

## 手动安装依赖

若自动安装失败，可手动安装系统依赖：

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y aria2 git-lfs

# Fedora
sudo dnf install -y aria2 git-lfs

# Arch
sudo pacman -S aria2 git-lfs

# macOS
brew install aria2 git-lfs
```

## 目录结构

项目源码：

```
ez-hfd-py-cli/
├── hfd.py                 # 入口脚本
├── hfd_cli/
│   ├── config.py          # 配置读写
│   ├── installer.py       # 依赖检测与自动安装
│   ├── hfd_manager.py     # hfd.sh 下载与管理
│   ├── repo.py            # 仓库文件列表 API
│   ├── downloader.py      # 调用 hfd.sh 下载
│   └── cli.py             # 命令行交互
├── requirements.txt
├── LICENSE
└── README.md
```

运行期数据目录：

```
~/.ezhfd/
├── config.json            # 持久化配置（首次配置时生成）
├── hfd.sh                 # 首次运行时自动下载
└── models/
    └── <org>/<repo>/      # 下载的模型文件
```

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
