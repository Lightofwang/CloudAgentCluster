#!/usr/bin/env python3
"""
零模型 API 消耗的 Hackathon Spec & Plan 入库脚本。
支持解析 GitHub Issue Markdown、表单 JSON 数据包，并更新 site/data/specs/<slug>/ 与 site/data/hackathons.json。
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

TZ_CN = timezone(timedelta(hours=8))
DEFAULT_ALLOWED_OWNER = "Lightofwang"
# 仅存储单向不可逆的 SHA-256 哈希，不在公开仓库保存明文口令
DEFAULT_PASSCODE_HASH = "4ac4e2244373f3c0bdfd4d735076cdd1190f7fbb0e7fee4e9b4c943714b5249e"


def expected_passcode_hash() -> str:
    secret = os.environ.get("HUB_PASSCODE", "").strip()
    if secret:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return DEFAULT_PASSCODE_HASH


def verify_submission_auth(
    payload: dict[str, Any],
    actor: str | None = None,
    require_auth: bool = False,
    allowed_owner: str | None = None,
) -> None:
    """校验提交者身份及提交口令哈希，防止未授权外部提交。"""
    owner = (allowed_owner or os.environ.get("HUB_ALLOWED_OWNER", "") or DEFAULT_ALLOWED_OWNER).strip()
    if actor is not None and actor.strip().lower() != owner.lower():
        raise PermissionError(f"拒绝入库：仅允许仓库所有者 {owner} 提交（当前提交者：{actor}）")

    if not require_auth:
        return

    exp_hash = expected_passcode_hash()
    raw_passcode = str(payload.get("passcode", "")).strip()
    provided_hash = str(payload.get("auth_hash", "")).strip().lower()
    if raw_passcode:
        provided_hash = hashlib.sha256(raw_passcode.encode("utf-8")).hexdigest()

    if not provided_hash or not hmac.compare_digest(provided_hash, exp_hash):
        raise PermissionError("拒绝入库：提交口令校验失败")


def now_iso() -> str:
    return datetime.now(TZ_CN).replace(microsecond=0).isoformat()


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return cleaned[:64] or "hackathon-project"


def _extract_between(text: str, start_marker: str, end_marker: str) -> str | None:
    pattern = re.escape(start_marker) + r"(.*?)" + re.escape(end_marker)
    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group(1).strip() if match else None


def _strip_code_fence(block: str) -> str:
    block = block.strip()
    match = re.match(r"^```[a-zA-Z0-9_-]*\s*\n(.*?)\n```$", block, flags=re.DOTALL)
    return match.group(1).strip() if match else block


def _parse_issue_form_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key: str | None = None
    buffer: list[str] = []

    for line in body.splitlines():
        heading_match = re.match(r"^###\s+(.+?)\s*$", line)
        if heading_match:
            if current_key is not None:
                sections[current_key] = "\n".join(buffer).strip()
            current_key = heading_match.group(1).strip()
            buffer = []
        elif current_key is not None:
            buffer.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(buffer).strip()
    return sections


def _clean_form_value(val: str | None) -> str:
    if not val:
        return ""
    text = val.strip()
    return "" if text in {"_No response_", "No response", "N/A"} else text


def parse_issue_markdown(body: str, title: str = "") -> dict[str, Any]:
    """从 GitHub Issue 正文中解析结构化元信息、Spec 与 Plan，或识别 reset_slug 触发指令。"""
    normalized = (body or "").replace("\r\n", "\n")

    # 1. 检查是否为触发重新开发指令
    trigger_block = _extract_between(normalized, "<!--TRIGGER_DEV_START-->", "<!--TRIGGER_DEV_END-->")
    if trigger_block:
        trigger_json = json.loads(_strip_code_fence(trigger_block))
        if trigger_json.get("reset_slug"):
            return {
                "action": "reset",
                "reset_slug": slugify(str(trigger_json["reset_slug"])),
                "auth_hash": str(trigger_json.get("auth_hash", "")).strip(),
                "passcode": str(trigger_json.get("passcode", "")).strip(),
            }

    # 2. 检查是否为提交页生成的标记块格式
    meta_block = _extract_between(normalized, "<!--HACKATHON_META_START-->", "<!--HACKATHON_META_END-->")
    spec_block = _extract_between(normalized, "<!--SPEC_START-->", "<!--SPEC_END-->")
    plan_block = _extract_between(normalized, "<!--PLAN_START-->", "<!--PLAN_END-->")
    submission_block = _extract_between(normalized, "<!--SUBMISSION_START-->", "<!--SUBMISSION_END-->")

    if meta_block and (
        (spec_block is not None and plan_block is not None) or submission_block is not None
    ):
        meta = json.loads(_strip_code_fence(meta_block))
        meta.setdefault("title", re.sub(r"^\[Hackathon Spec\]\s*", "", title).strip())
        if spec_block is not None:
            meta["spec_content"] = spec_block
        if plan_block is not None:
            meta["plan_content"] = plan_block
        if submission_block is not None:
            meta["submission_content"] = submission_block
        return meta

    # 3. 回退解析 GitHub Issue Form (### 标题分段格式)
    sections = _parse_issue_form_sections(normalized)

    def pick(*keys: str, default: str = "") -> str:
        for k in keys:
            for sec_k, sec_v in sections.items():
                if k.lower() in sec_k.lower():
                    cleaned = _clean_form_value(sec_v)
                    if cleaned:
                        return cleaned
        return default

    parsed_title = pick("比赛名称", "Title", default=re.sub(r"^\[Hackathon Spec\]\s*", "", title).strip())
    raw_slug = pick("唯一标识", "Slug", default="")
    slug = slugify(raw_slug or parsed_title)
    platform = pick("所属平台", "Platform", default="devpost").lower()
    if "lablab" in platform:
        platform = "lablab"
    elif "dora" in platform:
        platform = "dorahacks"
    elif "devpost" in platform:
        platform = "devpost"
    elif platform not in {"devpost", "lablab", "dorahacks", "other"}:
        platform = "other"

    tags_raw = pick("标签", "Tags", default="AI Agent, Full-Stack")
    tags = [t.strip() for t in re.split(r"[,，]", tags_raw) if t.strip()]

    score_raw = pick("匹配度评分", "Match Score", default="90")
    try:
        match_score = max(1, min(100, int(re.findall(r"\d+", score_raw)[0])))
    except (IndexError, ValueError):
        match_score = 90

    spec_content = pick("Spec 设计文档", "Spec", default="")
    plan_content = pick("Plan 实施计划", "Plan", default="")
    submission_content = pick("后续参赛提交清单", "Submission", default="")

    if not parsed_title or not spec_content or not plan_content:
        raise ValueError("Issue 正文中缺少必填字段（比赛名称、Spec 设计文档或 Plan 实施计划）")

    return {
        "slug": slug,
        "title": parsed_title,
        "platform": platform,
        "source_url": pick("比赛链接", "Source URL", default=""),
        "deadline": pick("截止日期", "Deadline", default="TBD"),
        "prize_pool": pick("奖金池", "Prize Pool", default="TBD"),
        "match_score": match_score,
        "tags": tags,
        "summary": pick("一句话简介", "Summary", default="由 Muse AI 自动分析提交的 Hackathon 设计规范。"),
        "project_type": pick("项目形态", "Project Type", default="fullstack-web"),
        "passcode": pick("安全提交口令", "Passcode", default=""),
        "spec_content": spec_content,
        "plan_content": plan_content,
        "submission_content": submission_content,
    }


def load_hackathons_index(root_dir: Path) -> dict[str, Any]:
    index_path = root_dir / "site" / "data" / "hackathons.json"
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    return {
        "updated_at": now_iso(),
        "site_config": {
            "github_owner": "Lightofwang",
            "github_repo": "CloudAgentCluster",
            "default_branch": "main",
        },
        "hackathons": [],
    }


def save_hackathons_index(root_dir: Path, data: dict[str, Any]) -> Path:
    index_path = root_dir / "site" / "data" / "hackathons.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index_path


def ingest_entry(
    payload: dict[str, Any],
    root_dir: Path,
    actor: str | None = None,
    require_auth: bool = False,
) -> dict[str, Any]:
    """将一条 Hackathon Spec/Plan 写入 site/data/specs/<slug>/ 并更新 site/data/hackathons.json。"""
    verify_submission_auth(payload, actor=actor, require_auth=require_auth)

    if payload.get("action") == "reset" and payload.get("reset_slug"):
        return reset_slug_status(str(payload["reset_slug"]), root_dir, actor=actor)

    title = str(payload.get("title", "")).strip()
    spec_content = str(payload.get("spec_content", "")).strip()
    plan_content = str(payload.get("plan_content", "")).strip()
    submission_content = str(payload.get("submission_content", "")).strip()
    submission_only = bool(payload.get("submission_only"))

    slug = slugify(str(payload.get("slug") or title))
    index_data = load_hackathons_index(root_dir)
    hackathons: list[dict[str, Any]] = index_data.setdefault("hackathons", [])

    existing_idx = next((i for i, h in enumerate(hackathons) if h.get("slug") == slug), None)
    existing = hackathons[existing_idx] if existing_idx is not None else {}

    spec_dir = root_dir / "site" / "data" / "specs" / slug
    spec_dir.mkdir(parents=True, exist_ok=True)

    if submission_only:
        if not existing:
            raise KeyError(f"submission_only 模式未找到已有比赛 slug='{slug}'")
        if not submission_content:
            raise ValueError("submission_only 模式必须提供 submission_content")
        (spec_dir / "submission.md").write_text(submission_content + "\n", encoding="utf-8")
        existing["submission_path"] = f"data/specs/{slug}/submission.md"
        (spec_dir / "meta.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_hackathons_index(root_dir, index_data)
        return existing

    if not title or not spec_content or not plan_content:
        raise ValueError("payload 必须包含 title、spec_content 和 plan_content")

    (spec_dir / "spec.md").write_text(spec_content + "\n", encoding="utf-8")
    (spec_dir / "plan.md").write_text(plan_content + "\n", encoding="utf-8")
    if submission_content:
        (spec_dir / "submission.md").write_text(submission_content + "\n", encoding="utf-8")

    tags = payload.get("tags") or ["AI Agent", "Full-Stack"]
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[,，]", tags) if t.strip()]

    now = now_iso()

    entry = {
        "id": slug,
        "slug": slug,
        "title": title,
        "platform": str(payload.get("platform") or existing.get("platform") or "devpost").lower(),
        "source_url": str(payload.get("source_url") or existing.get("source_url") or ""),
        "deadline": str(payload.get("deadline") or existing.get("deadline") or "TBD"),
        "prize_pool": str(payload.get("prize_pool") or existing.get("prize_pool") or "TBD"),
        "tags": tags,
        "match_score": int(payload.get("match_score") or existing.get("match_score") or 90),
        "status": "pending_dev",
        "spec_path": f"data/specs/{slug}/spec.md",
        "plan_path": f"data/specs/{slug}/plan.md",
        "submission_path": (
            f"data/specs/{slug}/submission.md"
            if submission_content or existing.get("submission_path")
            else ""
        ),
        "project_type": str(payload.get("project_type") or existing.get("project_type") or "fullstack-web"),
        "summary": str(payload.get("summary") or existing.get("summary") or ""),
        "submitted_by": actor.strip() if actor else str(payload.get("submitted_by") or DEFAULT_ALLOWED_OWNER),
        "repo_url": str(existing.get("repo_url") or ""),
        "fallback_path": f"projects/{slug}",
        "created_at": str(existing.get("created_at") or now),
        "completed_at": "",
    }

    (spec_dir / "meta.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if existing_idx is not None:
        hackathons.pop(existing_idx)
    hackathons.insert(0, entry)

    save_hackathons_index(root_dir, index_data)
    return entry


def reset_slug_status(slug: str, root_dir: Path, actor: str | None = None) -> dict[str, Any]:
    """将指定 slug 的状态重置为 pending_dev，用于一键重新触发开发。"""
    verify_submission_auth({}, actor=actor, require_auth=False)
    normalized_slug = slugify(slug)
    index_data = load_hackathons_index(root_dir)
    hackathons: list[dict[str, Any]] = index_data.setdefault("hackathons", [])

    target = next((h for h in hackathons if h.get("slug") == normalized_slug), None)
    if target is None:
        raise KeyError(f"未在 hackathons.json 中找到 slug='{normalized_slug}'")

    target["status"] = "pending_dev"
    target["completed_at"] = ""

    meta_path = root_dir / "site" / "data" / "specs" / normalized_slug / "meta.json"
    if meta_path.exists():
        meta_path.write_text(json.dumps(target, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save_hackathons_index(root_dir, index_data)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="入库 Hackathon Spec & Plan 至网站队列")
    parser.add_argument("--root-dir", default=str(Path(__file__).resolve().parent.parent), help="仓库根目录路径")
    parser.add_argument("--input-json", help="输入 JSON 文件路径")
    parser.add_argument("--issue-body-file", help="GitHub Issue 正文文件路径")
    parser.add_argument("--issue-title", default="", help="GitHub Issue 标题")
    parser.add_argument("--reset-slug", help="将指定 slug 状态重置为 pending_dev")
    parser.add_argument("--actor", default=None, help="提交者 GitHub 用户名（用于权限校验）")
    parser.add_argument("--require-auth", action="store_true", help="强制校验提交口令哈希")
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()

    if args.reset_slug:
        entry = reset_slug_status(args.reset_slug, root_dir, actor=args.actor)
        print(json.dumps({"action": "reset", "entry": entry}, ensure_ascii=False, indent=2))
        return 0

    if args.input_json:
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        entry = ingest_entry(payload, root_dir, actor=args.actor, require_auth=args.require_auth)
        print(json.dumps({"action": "ingest_json", "entry": entry}, ensure_ascii=False, indent=2))
        return 0

    if args.issue_body_file:
        body_text = Path(args.issue_body_file).read_text(encoding="utf-8")
        payload = parse_issue_markdown(body_text, title=args.issue_title)
        entry = ingest_entry(payload, root_dir, actor=args.actor, require_auth=args.require_auth)
        print(json.dumps({"action": "ingest_issue", "entry": entry}, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
