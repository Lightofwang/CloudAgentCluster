#!/usr/bin/env python3
"""
Antigravity 下游队列读取与状态同步器。
支持从已部署的中转网站 URL (如 GitHub Pages) 或本地仓库读取 pending_dev 任务，
缓存 spec.md / plan.md 到本地，并回写 in_progress / completed / failed 状态。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ingest_spec import load_hackathons_index, now_iso, save_hackathons_index, slugify  # noqa: E402

VALID_STATUSES = {"pending_dev", "in_progress", "completed", "failed"}


def _http_get_text(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CloudAgentCluster-Sync/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def try_git_pull(root_dir: Path) -> tuple[bool, str]:
    git_dir = root_dir / ".git"
    if not git_dir.exists():
        return False, "当前目录未初始化 Git"
    remote_check = subprocess.run(
        ["git", "-C", str(root_dir), "remote"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not remote_check.stdout.strip():
        return False, "未配置 Git remote，跳过 git pull"

    res = subprocess.run(
        ["git", "-C", str(root_dir), "pull", "--rebase"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode == 0:
        return True, res.stdout.strip() or "git pull 成功"
    return False, (res.stderr or res.stdout).strip()


def sync_from_site_url(site_url: str, root_dir: Path, target_slug: str | None = None) -> dict[str, Any]:
    """从网站 URL 拉取 data/hackathons.json 并将匹配的 spec.md / plan.md 缓存到本地。"""
    base = site_url.rstrip("/")
    index_url = f"{base}/data/hackathons.json"
    remote_index = json.loads(_http_get_text(index_url))

    local_index = load_hackathons_index(root_dir)
    local_map = {h["slug"]: h for h in local_index.get("hackathons", []) if h.get("slug")}

    merged_list: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()

    for item in remote_index.get("hackathons", []):
        slug = item.get("slug")
        if not slug:
            continue
        seen_slugs.add(slug)

        if target_slug is None or slug == target_slug:
            spec_dir = root_dir / "site" / "data" / "specs" / slug
            spec_dir.mkdir(parents=True, exist_ok=True)
            spec_rel = item.get("spec_path") or f"data/specs/{slug}/spec.md"
            plan_rel = item.get("plan_path") or f"data/specs/{slug}/plan.md"

            try:
                spec_text = _http_get_text(f"{base}/{spec_rel.lstrip('/')}")
                (spec_dir / "spec.md").write_text(spec_text, encoding="utf-8")
            except urllib.error.URLError:
                pass

            try:
                plan_text = _http_get_text(f"{base}/{plan_rel.lstrip('/')}")
                (spec_dir / "plan.md").write_text(plan_text, encoding="utf-8")
            except urllib.error.URLError:
                pass

            (spec_dir / "meta.json").write_text(
                json.dumps(item, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        merged_list.append(item)

    # 保留仅存在本地但尚未同步到网站的新增条目
    for slug, local_item in local_map.items():
        if slug not in seen_slugs:
            merged_list.append(local_item)

    if remote_index.get("site_config"):
        local_index["site_config"] = remote_index["site_config"]
    local_index["hackathons"] = merged_list
    save_hackathons_index(root_dir, local_index)
    return local_index


def attach_local_paths(entry: dict[str, Any], root_dir: Path) -> dict[str, Any]:
    slug = entry["slug"]
    enriched = dict(entry)
    enriched["local_spec_path"] = (root_dir / "site" / "data" / "specs" / slug / "spec.md").as_posix()
    enriched["local_plan_path"] = (root_dir / "site" / "data" / "specs" / slug / "plan.md").as_posix()
    enriched["local_project_dir"] = (root_dir / "projects" / slug).as_posix()
    return enriched


def mark_status(
    slug: str,
    status: str,
    root_dir: Path,
    repo_url: str | None = None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"无效状态 '{status}'，可选值：{sorted(VALID_STATUSES)}")

    normalized_slug = slugify(slug)
    index_data = load_hackathons_index(root_dir)
    target = next(
        (h for h in index_data.get("hackathons", []) if h.get("slug") == normalized_slug),
        None,
    )
    if target is None:
        raise KeyError(f"未找到 slug='{normalized_slug}' 的比赛记录")

    target["status"] = status
    if repo_url is not None and repo_url.strip():
        target["repo_url"] = repo_url.strip()
    if status == "completed":
        target["completed_at"] = now_iso()
    elif status == "pending_dev":
        target["completed_at"] = ""

    meta_path = root_dir / "site" / "data" / "specs" / normalized_slug / "meta.json"
    if meta_path.parent.exists():
        meta_path.write_text(json.dumps(target, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save_hackathons_index(root_dir, index_data)
    return attach_local_paths(target, root_dir)


def resolve_index(root_dir: Path, site_url: str | None, pull: bool, target_slug: str | None = None) -> dict[str, Any]:
    if pull:
        ok, msg = try_git_pull(root_dir)
        print(f"[git pull] {msg}", file=sys.stderr)

    effective_url = site_url or os.environ.get("HACKATHON_HUB_URL", "").strip()
    if effective_url:
        try:
            return sync_from_site_url(effective_url, root_dir, target_slug=target_slug)
        except Exception as exc:
            if site_url:
                raise RuntimeError(f"从网站 {effective_url} 读取失败: {exc}") from exc
            print(f"[warn] 环境变量 HACKATHON_HUB_URL 读取失败，回退本地数据: {exc}", file=sys.stderr)

    return load_hackathons_index(root_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="读取中转网站 Hackathon 队列并管理开发状态")
    subparsers = parser.add_subparsers(dest="command", required=True)

    default_root = str(Path(__file__).resolve().parent.parent)

    p_list = subparsers.add_parser("list", help="列出指定状态的 Hackathon 任务")
    p_list.add_argument("--root-dir", default=default_root)
    p_list.add_argument("--status", default="", help="按状态过滤，如 pending_dev")
    p_list.add_argument("--site-url", default="", help="中转网站根 URL，例如 https://lightofwang.github.io/CloudAgentCluster")
    p_list.add_argument("--pull", action="store_true", help="读取前先尝试 git pull")
    p_list.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    p_get = subparsers.add_parser("get", help="获取单个比赛的详细信息与 Spec/Plan 本地路径")
    p_get.add_argument("--root-dir", default=default_root)
    p_get.add_argument("--slug", required=True)
    p_get.add_argument("--site-url", default="")

    p_mark = subparsers.add_parser("mark", help="更新比赛开发状态")
    p_mark.add_argument("--root-dir", default=default_root)
    p_mark.add_argument("--slug", required=True)
    p_mark.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    p_mark.add_argument("--repo-url", default="")

    args = parser.parse_args()
    root_dir = Path(args.root_dir).resolve()

    if args.command == "list":
        index_data = resolve_index(root_dir, args.site_url or None, args.pull)
        items = index_data.get("hackathons", [])
        if args.status:
            items = [h for h in items if h.get("status") == args.status]
        enriched = [attach_local_paths(h, root_dir) for h in items]
        if args.json:
            print(json.dumps(enriched, ensure_ascii=False, indent=2))
        else:
            if not enriched:
                print("当前队列中没有符合条件的 Hackathon 任务。")
            for item in enriched:
                print(
                    f"- [{item.get('status')}] {item.get('slug')} | {item.get('title')} "
                    f"({item.get('platform')})\n"
                    f"  Spec: {item['local_spec_path']}\n"
                    f"  Plan: {item['local_plan_path']}"
                )
        return 0

    if args.command == "get":
        target_slug = slugify(args.slug)
        index_data = resolve_index(root_dir, args.site_url or None, False, target_slug=target_slug)
        target = next((h for h in index_data.get("hackathons", []) if h.get("slug") == target_slug), None)
        if target is None:
            print(f"未找到 slug='{target_slug}'", file=sys.stderr)
            return 1
        print(json.dumps(attach_local_paths(target, root_dir), ensure_ascii=False, indent=2))
        return 0

    if args.command == "mark":
        updated = mark_status(args.slug, args.status, root_dir, repo_url=args.repo_url or None)
        print(json.dumps(updated, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
