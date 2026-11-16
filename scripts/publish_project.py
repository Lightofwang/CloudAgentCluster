#!/usr/bin/env python3
"""
验证已开发的 Hackathon 项目并推送到 GitHub：
1. 运行 projects/<slug>/tests/ 单元测试（测试失败则阻止推送）；
2. 模式 A（优先）：若存在 GITHUB_TOKEN / GH_TOKEN，则调用 GitHub API 创建独立仓库 hackathon-<slug> 并推送；
3. 模式 B（兜底）：若无建库 Token 或 API 受限，无缝存入主仓库 projects/<slug>/ 目录并推送；
4. 回写 site/data/hackathons.json 状态为 completed 并填充 repo_url。
"""

from __future__ import annotations

import argparse
import base64
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

from ingest_spec import load_hackathons_index, slugify  # noqa: E402
from sync_and_queue import mark_status  # noqa: E402


def run_project_tests(project_dir: Path) -> tuple[bool, str]:
    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        return True, "未发现 tests/ 目录，跳过测试"

    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(tests_dir), "-p", "test_*.py", "-v"],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (res.stdout + "\n" + res.stderr).strip()
    return res.returncode == 0, output


def create_github_repo(owner: str, repo_name: str, description: str, token: str) -> str:
    payload = json.dumps(
        {
            "name": repo_name,
            "description": description[:250],
            "private": False,
            "auto_init": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "CloudAgentCluster-Publisher/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["html_url"]
    except urllib.error.HTTPError as err:
        if err.code == 422:
            # 仓库可能已存在，直接返回标准 URL
            return f"https://github.com/{owner}/{repo_name}"
        raise


def push_standalone_repo(project_dir: Path, owner: str, repo_name: str, token: str) -> None:
    remote_url = f"https://github.com/{owner}/{repo_name}.git"
    basic_auth = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")

    cmds = [
        ["git", "-C", str(project_dir), "init", "-b", "main"],
        ["git", "-C", str(project_dir), "add", "-A"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")

    status_res = subprocess.run(
        ["git", "-C", str(project_dir), "status", "--porcelain"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if status_res.stdout.strip():
        subprocess.run(
            ["git", "-C", str(project_dir), "commit", "-m", f"feat: initial hackathon submission ({repo_name})"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    subprocess.run(
        [
            "git",
            "-C",
            str(project_dir),
            "-c",
            f"http.extraHeader=Authorization: Basic {basic_auth}",
            "push",
            "-u",
            remote_url,
            "main",
            "--force",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def commit_and_push_monorepo(root_dir: Path, slug: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "dry-run 模式：跳过主仓库 git commit/push"

    git_dir = root_dir / ".git"
    if not git_dir.exists():
        return False, "主仓库未初始化 .git"

    subprocess.run(
        ["git", "-C", str(root_dir), "add", "site/data/", f"projects/{slug}/"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    diff_res = subprocess.run(
        ["git", "-C", str(root_dir), "diff", "--cached", "--quiet"],
        capture_output=True,
    )
    if diff_res.returncode != 0:
        subprocess.run(
            ["git", "-C", str(root_dir), "commit", "-m", f"feat(hackathon): complete and publish '{slug}'"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    remote_res = subprocess.run(
        ["git", "-C", str(root_dir), "remote"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not remote_res.stdout.strip():
        return True, "本地已提交 commit（尚未配置远程 origin，未执行 git push）"

    push_res = subprocess.run(
        ["git", "-C", str(root_dir), "push", "-u", "origin", "main"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if push_res.returncode == 0:
        return True, "主仓库已推送到 origin/main"
    return False, (push_res.stderr or push_res.stdout).strip()


def publish_project(
    slug: str,
    root_dir: Path,
    owner: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    normalized_slug = slugify(slug)
    project_dir = root_dir / "projects" / normalized_slug
    if not project_dir.exists():
        raise FileNotFoundError(f"项目目录不存在: {project_dir}")

    # 1. 运行项目单元测试
    passed, test_output = run_project_tests(project_dir)
    if not passed:
        mark_status(normalized_slug, "failed", root_dir)
        raise RuntimeError(f"项目 {normalized_slug} 测试未通过，中止发布：\n{test_output}")

    index_data = load_hackathons_index(root_dir)
    site_cfg = index_data.get("site_config", {})
    github_owner = owner or site_cfg.get("github_owner") or "Lightofwang"
    github_repo = site_cfg.get("github_repo") or "CloudAgentCluster"
    default_branch = site_cfg.get("default_branch") or "main"

    entry = next((h for h in index_data.get("hackathons", []) if h.get("slug") == normalized_slug), {})
    title = entry.get("title", normalized_slug)

    # 2. 优先尝试创建独立 GitHub 仓库，否则自动兜底主仓库子目录
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    standalone_name = f"hackathon-{normalized_slug}"
    mode = "monorepo-fallback"
    repo_url = f"https://github.com/{github_owner}/{github_repo}/tree/{default_branch}/projects/{normalized_slug}"
    publish_note = ""

    if token and not dry_run:
        try:
            created_url = create_github_repo(
                github_owner,
                standalone_name,
                f"Hackathon submission for {title}",
                token,
            )
            push_standalone_repo(project_dir, github_owner, standalone_name, token)
            repo_url = created_url
            mode = "standalone-repo"
            publish_note = f"已创建并推送独立 GitHub 仓库: {repo_url}"
        except Exception as exc:
            publish_note = f"独立仓库推送失败({exc})，已自动降级为 Monorepo 兜底路径: {repo_url}"
    else:
        if dry_run:
            publish_note = f"dry-run 模式：模拟发布至兜底路径 {repo_url}"
        else:
            publish_note = f"未检测到 GITHUB_TOKEN，已启用自动兜底模式，归档至 {repo_url}"

    # 3. 回写状态为 completed
    updated_entry = mark_status(normalized_slug, "completed", root_dir, repo_url=repo_url)

    # 4. 同步主仓库（更新网站队列数据及兜底目录）
    mono_ok, mono_msg = commit_and_push_monorepo(root_dir, normalized_slug, dry_run=dry_run)

    return {
        "slug": normalized_slug,
        "mode": mode,
        "dry_run": dry_run,
        "repo_url": repo_url,
        "tests_passed": passed,
        "publish_note": publish_note,
        "monorepo_sync": {"ok": mono_ok, "message": mono_msg},
        "entry": updated_entry,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证并发布已开发的 Hackathon 项目到 GitHub")
    parser.add_argument("--slug", required=True, help="比赛 Slug")
    parser.add_argument("--root-dir", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--owner", default="", help="GitHub 用户名（默认读取 site_config）")
    parser.add_argument("--dry-run", action="store_true", help="只运行测试并模拟状态更新，不执行远程推送")
    args = parser.parse_args()

    result = publish_project(
        slug=args.slug,
        root_dir=Path(args.root_dir).resolve(),
        owner=args.owner or None,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
