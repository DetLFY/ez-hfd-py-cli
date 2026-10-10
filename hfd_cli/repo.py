"""通过 Hugging Face HTTP API 获取仓库文件列表。

使用官方（或镜像）的 tree 接口：

    GET {site}/api/models/{repo_id}/tree/{revision}?recursive=true&expand=false

接口会分页返回结果，通过响应头 ``Link: <...>; rel="next"`` 指向下一页。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

_USER_AGENT = "ezhfd-py-cli/1.0"


class RepoError(Exception):
    """获取仓库信息失败。"""


class RepoNotFoundError(RepoError):
    """仓库不存在。"""


class RepoAuthError(RepoError):
    """仓库需要授权（私有 / gated）。"""


def _next_link(link_header: Optional[str]) -> Optional[str]:
    """从 ``Link`` 响应头里取出 ``rel="next"`` 的 URL。"""
    if not link_header:
        return None
    for part in link_header.split(","):
        match = re.search(r"<([^>]+)>\s*;\s*rel\s*=\s*\"?next\"?", part)
        if match:
            return match.group(1)
    return None


def _get_json(url: str, token: Optional[str]) -> Tuple[object, Optional[str]]:
    """GET 一个 URL 并解析 JSON，同时返回 Link 响应头。"""
    headers = {"User-Agent": _USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
            link = response.headers.get("Link")
        return payload, link
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RepoAuthError(
                "仓库需要授权（私有或 gated）。请设置环境变量 HF_TOKEN 后重试。"
            ) from exc
        if exc.code == 404:
            raise RepoNotFoundError("仓库或分支不存在，请检查仓库名是否正确。") from exc
        raise RepoError(f"请求失败（HTTP {exc.code}）：{url}") from exc
    except urllib.error.URLError as exc:
        raise RepoError(f"网络错误：{exc.reason}") from exc


def fetch_repo_files(
    site: str,
    repo_id: str,
    revision: str = "main",
    token: Optional[str] = None,
    is_dataset: bool = False,
) -> List[Dict[str, object]]:
    """获取仓库的全部文件，返回 ``[{"path": ..., "size": ...}, ...]``。"""
    base = site.rstrip("/")
    kind = "datasets" if is_dataset else "models"
    repo = urllib.parse.quote(repo_id, safe="/")
    rev = urllib.parse.quote(revision, safe="/")
    url: Optional[str] = (
        f"{base}/api/{kind}/{repo}/tree/{rev}?recursive=true&expand=false"
    )

    files: List[Dict[str, object]] = []
    seen = set()

    while url:
        payload, link = _get_json(url, token)
        if not isinstance(payload, list):
            raise RepoError("仓库返回了非预期的数据格式。")
        for item in payload:
            if not isinstance(item, dict) or item.get("type") != "file":
                continue
            path = item.get("path")
            if not path or path in seen:
                continue
            seen.add(path)
            files.append({"path": path, "size": int(item.get("size") or 0)})
        url = _next_link(link)

    files.sort(key=lambda item: str(item["path"]))
    return files
