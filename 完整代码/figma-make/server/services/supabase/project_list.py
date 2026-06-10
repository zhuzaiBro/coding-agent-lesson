"""解析 Supabase MCP list_projects 并拉取可访问项目列表。"""
import json
import re
from typing import Any, Dict, List

from config.supabase import build_org_mcp_url
from services.supabase.mcp_client import SupabaseMCPClient


def parse_list_projects_response(raw: str) -> List[Dict[str, Any]]:
    """将 MCP list_projects 文本/JSON 规范化为 [{ref, name, region?}]。"""
    text = (raw or "").strip()
    if not text:
        return []

    candidates: Any = None
    try:
        candidates = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                candidates = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []

    if isinstance(candidates, dict):
        if isinstance(candidates.get("projects"), list):
            rows = candidates["projects"]
        else:
            rows = [candidates]
    elif isinstance(candidates, list):
        rows = candidates
    else:
        return []

    projects: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ref = (
            row.get("ref")
            or row.get("id")
            or row.get("project_ref")
            or row.get("project_id")
        )
        if not ref:
            continue
        ref_str = str(ref).strip()
        if not ref_str or ref_str in seen:
            continue
        seen.add(ref_str)
        name = (
            row.get("name")
            or row.get("project_name")
            or row.get("title")
            or ref_str
        )
        entry: Dict[str, Any] = {
            "ref": ref_str,
            "name": str(name).strip() or ref_str,
        }
        region = row.get("region") or row.get("organization_id")
        if region:
            entry["region"] = str(region)
        projects.append(entry)

    return projects


async def fetch_accessible_projects(access_token: str) -> List[Dict[str, Any]]:
    """使用账号级 MCP（无 project_ref）列出 OAuth 用户可访问的项目。"""
    client = SupabaseMCPClient(
        url=build_org_mcp_url(),
        access_token=access_token,
    )
    raw = await client.call_tool_raw("list_projects", {})
    projects = parse_list_projects_response(raw)
    if projects:
        return projects

    # 兜底：部分账号仅返回单个 project URL
    try:
        url_text = (await client.call_tool_raw("get_project_url", {})).strip()
        match = re.search(r"https?://([a-z0-9]{10,30})\.supabase\.co", url_text, re.I)
        if match:
            ref = match.group(1)
            return [{"ref": ref, "name": ref, "source": "get_project_url"}]
    except Exception:
        pass

    return projects
