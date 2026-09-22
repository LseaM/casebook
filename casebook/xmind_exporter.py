"""Create an editable XMind handoff from cases in the active Casebook scope.

Modified by AITest: add XMind export and guard AITest canonical projections.
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .scanner import CasebookStore, resolve_project_path


class XMindExportError(ValueError):
    """A requested handoff would include invalid or stale case data."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tag_values(tags: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for tag in tags:
        key, separator, value = str(tag).partition(":")
        if separator and key.startswith("aitest-"):
            if key in values:
                raise XMindExportError(f"duplicate AITest binding tag: {key}")
            values[key] = value
    return values


def _bound_path(root: Path, value: str, label: str) -> Path:
    if not value or Path(value).is_absolute():
        raise XMindExportError(f"invalid {label} binding")
    path = (root / value).resolve()
    if root.resolve() not in path.parents:
        raise XMindExportError(f"{label} binding escapes the AITest project")
    return path


def validate_aitest_projection(project_root: Path, file_path: str) -> None:
    """Refuse a handoff when an AITest review copy differs from formal YAML."""
    projected_path = resolve_project_path(project_root, file_path)
    yaml = YAML(typ="safe")
    try:
        projected = yaml.load(projected_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, YAMLError) as exc:
        raise XMindExportError(f"cannot read Casebook file: {file_path}") from exc
    if not isinstance(projected, dict):
        raise XMindExportError(f"invalid Casebook file: {file_path}")
    metadata = projected.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise XMindExportError(f"invalid Casebook metadata: {file_path}")
    raw_tags = metadata.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    if not isinstance(raw_tags, list):
        raise XMindExportError(f"invalid Casebook tags: {file_path}")
    tags = _tag_values(raw_tags)
    if not tags:
        if (project_root.resolve().parent / "schema" / "traceability-schema.json").exists():
            raise XMindExportError(f"AITest source binding is missing: {file_path}")
        return
    required = {
        "aitest-canonical-path", "aitest-canonical-sha256",
        "aitest-traceability-path", "aitest-traceability-sha256",
    }
    if not required.issubset(tags):
        raise XMindExportError(f"incomplete AITest source binding: {file_path}")
    if tags["aitest-canonical-path"].replace("\\", "/") != file_path:
        raise XMindExportError(f"AITest canonical path does not match review copy: {file_path}")
    source_root = project_root.resolve().parent
    canonical = _bound_path(source_root, tags["aitest-canonical-path"], "canonical")
    traceability = _bound_path(source_root, tags["aitest-traceability-path"], "traceability")
    try:
        if _sha256(canonical) != tags["aitest-canonical-sha256"]:
            raise XMindExportError(f"formal cases changed after Casebook export: {file_path}")
        if _sha256(traceability) != tags["aitest-traceability-sha256"]:
            raise XMindExportError(f"traceability changed after Casebook export: {file_path}")
        formal = yaml.load(canonical.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, YAMLError) as exc:
        raise XMindExportError(f"cannot validate AITest source binding: {file_path}") from exc
    if not isinstance(formal, dict) or projected.get("test_cases") != formal.get("test_cases"):
        raise XMindExportError(f"Casebook review copy differs from formal cases: {file_path}")
    for field in ("module", "feature"):
        if metadata.get(field) != (formal.get("metadata") or {}).get(field):
            raise XMindExportError(f"Casebook {field} differs from formal cases: {file_path}")


def collect_cases(store: CasebookStore, selection: list[dict[str, str]] | None) -> list[dict[str, Any]]:
    """Resolve explicit file/ID pairs or the complete scanned scope."""
    files = store.list_files()
    known: dict[tuple[str, str], dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for file_item in files:
        entry = store.get_file(file_item["path"])
        if not entry:
            continue
        for case in entry["cases"]:
            key = (entry["path"], case["id"])
            if key in known:
                raise XMindExportError(f"duplicate case in scan scope: {key}")
            item = {"file_path": entry["path"], "module": entry["module"], "feature": entry["feature"], **case}
            known[key] = item
            ordered.append(item)
    if selection is None:
        chosen = ordered
    else:
        if not isinstance(selection, list) or not selection:
            raise XMindExportError("select at least one case")
        requested: set[tuple[str, str]] = set()
        for item in selection:
            if not isinstance(item, dict) or not isinstance(item.get("file_path"), str) or not isinstance(item.get("case_id"), str):
                raise XMindExportError("each selection needs file_path and case_id")
            key = (item["file_path"], item["case_id"])
            if key in requested:
                raise XMindExportError(f"duplicate selected case: {key}")
            if key not in known:
                raise XMindExportError(f"case is outside the active scope: {key}")
            requested.add(key)
        chosen = [item for item in ordered if (item["file_path"], item["id"]) in requested]
    if not chosen:
        raise XMindExportError("there are no cases to export")
    for file_path in {item["file_path"] for item in chosen}:
        validate_aitest_projection(store.project_root, file_path)
    return chosen


def _topic(title: str, children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"id": str(uuid.uuid4()), "title": title}
    if children:
        value["children"] = {"attached": children}
    return value


def _case_topic(case: dict[str, Any], mark_ai: bool) -> dict[str, Any]:
    prefix = "[AI]" if mark_ai else ""
    children = []
    if case.get("description"):
        children.append(_topic(f"说明：{case['description']}"))
    children.append(_topic(f"优先级：{case['priority']}｜类型：{case['type']}"))
    for key, title in (("preconditions", "前置条件"), ("steps", "操作步骤"), ("expected_results", "预期结果")):
        values = case.get(key) or []
        if values:
            children.append(_topic(title, [_topic(f"{index}. {value}") for index, value in enumerate(values, 1)]))
    return _topic(f"{prefix}[{case['id']}] {case['title']}", children)


def build_xmind(cases: list[dict[str, Any]], mark_ai: bool = False) -> bytes:
    if not cases:
        raise XMindExportError("there are no cases to export")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[(case["module"], case["feature"])].append(_case_topic(case, mark_ai))
    branches = [_topic(f"{module} / {feature}", items) for (module, feature), items in grouped.items()]
    sheet = {
        "id": str(uuid.uuid4()), "class": "sheet", "title": "Casebook cases",
        "rootTopic": {**_topic("Casebook cases", branches), "class": "topic", "structureClass": "org.xmind.ui.logic.right"},
    }
    members = {
        "content.json": json.dumps([sheet], ensure_ascii=False, separators=(",", ":")),
        "metadata.json": json.dumps({"dataStructureVersion": "3", "creator": {"name": "Casebook", "version": "0.9.0"}}, ensure_ascii=False),
    }
    members["manifest.json"] = json.dumps({"file-entries": {name: {} for name in members}}, separators=(",", ":"))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content.encode("utf-8"))
    return buffer.getvalue()
