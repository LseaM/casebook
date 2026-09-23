"""AITest modification: XMind handoff from the Casebook review page."""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ruamel.yaml import YAML

from casebook.app import create_app


def write_cases(root: Path, relative: str = "releases/login.yaml") -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        """metadata:
  module: 账号
  feature: 登录
  owner: QA
  last_reviewed: '2026-09-22'
test_cases:
  - id: TC_LOGIN_001
    title: 正确凭据登录
    priority: P0
    type: functional
    preconditions: [用户已创建]
    steps: [输入账号和密码, 点击登录]
    expected_results: [进入首页]
  - id: TC_LOGIN_002
    title: 错误密码被拒绝
    priority: P1
    type: functional
    steps: [输入错误密码, 点击登录]
    expected_results: [停留在登录页]
""",
        encoding="utf-8",
    )
    return target


def exported_titles(content: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        sheet = json.loads(archive.read("content.json"))[0]
    groups = sheet["rootTopic"]["children"]["attached"]
    return [case["title"] for group in groups for case in group["children"]["attached"]]


class XMindExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = write_cases(self.root)
        self.app = create_app(self.root, ["releases"], watch=False)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_selected_and_all_export_keep_case_ids(self) -> None:
        selected = self.client.post("/api/export/xmind", json={
            "cases": [{"file_path": "releases/login.yaml", "case_id": "TC_LOGIN_002"}],
            "mark_ai": True,
        })
        self.assertEqual(selected.status_code, 200)
        self.assertIn("attachment", selected.headers["Content-Disposition"])
        self.assertEqual(exported_titles(selected.data), ["[AI][TC_LOGIN_002] 错误密码被拒绝"])
        self.assertEqual(len(exported_titles(self.client.post("/api/export/xmind", json={"all": True}).data)), 2)

    def test_invalid_or_out_of_scope_selection_is_rejected(self) -> None:
        for payload in (
            {"cases": []},
            {"cases": [{"file_path": "releases/login.yaml", "case_id": "TC_LOGIN_999"}]},
            {"cases": [{"file_path": "../other.yaml", "case_id": "TC_LOGIN_001"}]},
            {"all": True, "cases": []},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/api/export/xmind", json=payload).status_code, 400)

    def test_aitest_projection_edit_blocks_handoff(self) -> None:
        workspace = self.root / "casebook-workspace"
        schema = self.root / "schema" / "traceability-schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text("{}", encoding="utf-8")
        formal = write_cases(self.root, "releases/pilot-login/login.yaml")
        trace = self.root / "docs" / "traceability.yaml"
        trace.parent.mkdir(parents=True)
        trace.write_text("mappings: []\n", encoding="utf-8")
        projection = workspace / "releases" / "pilot-login" / "login.yaml"
        projection.parent.mkdir(parents=True)
        yaml = YAML(typ="safe")
        data = yaml.load(formal.read_text(encoding="utf-8"))
        data["metadata"]["tags"] = [
            "aitest-canonical-path:releases/pilot-login/login.yaml",
            f"aitest-canonical-sha256:{hashlib.sha256(formal.read_bytes()).hexdigest()}",
            "aitest-traceability-path:docs/traceability.yaml",
            f"aitest-traceability-sha256:{hashlib.sha256(trace.read_bytes()).hexdigest()}",
        ]
        with projection.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
        app = create_app(workspace, ["releases/pilot-login"], watch=False)
        client = app.test_client()
        self.assertEqual(client.post("/api/export/xmind", json={"all": True}).status_code, 200)
        data["test_cases"][0]["title"] = "页面临时改动"
        with projection.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
        response = client.post("/api/export/xmind", json={"all": True})
        self.assertEqual(response.status_code, 400)
        self.assertIn("differs from formal cases", response.get_json()["error"])
        data["test_cases"][0]["title"] = "正确凭据登录"
        data["metadata"].pop("tags")
        with projection.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
        response = client.post("/api/export/xmind", json={"all": True})
        self.assertEqual(response.status_code, 400)
        self.assertIn("binding is missing", response.get_json()["error"])

    def test_sdd_projection_uses_canonical_id_and_rejects_stale_content(self) -> None:
        source_root = self.root / "sdd"
        workspace = source_root / "casebook-workspace"
        (source_root / "schemas").mkdir(parents=True)
        (source_root / "schemas" / "case-set.schema.json").write_text("{}", encoding="utf-8")
        formal = source_root / "generated-cases" / "login" / "cases.yaml"
        formal.parent.mkdir(parents=True)
        formal.write_text("case_set_id: CASESET-LOGIN\ncases: []\n", encoding="utf-8")
        projection = workspace / "releases" / "login" / "cases.yaml"
        projection.parent.mkdir(parents=True)
        data = YAML(typ="safe").load(self.source.read_text(encoding="utf-8"))
        data["test_cases"][0]["traceability"] = {
            "canonical_id": "TC-LOGIN-000001", "revision": 1, "case_set_id": "CASESET-LOGIN",
            "requirement_refs": ["LOGIN-R-0001"], "coverage_refs": ["COV-LOGIN-001"],
            "evidence_refs": {"rule_ids": ["LOGIN-R-0001"]},
        }
        checksum_payload = {"module": data["metadata"]["module"], "feature": data["metadata"]["feature"], "test_cases": data["test_cases"]}
        checksum = hashlib.sha256(json.dumps(checksum_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        data["metadata"]["source_binding"] = {
            "canonical_path": "generated-cases/login/cases.yaml",
            "canonical_sha256": hashlib.sha256(formal.read_bytes()).hexdigest(),
            "case_set_id": "CASESET-LOGIN",
            "projection_sha256": checksum,
        }
        yaml = YAML()
        with projection.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
        client = create_app(workspace, ["releases/login"], watch=False).test_client()
        exported = client.post("/api/export/xmind", json={"all": True, "mark_ai": True})
        self.assertEqual(exported.status_code, 200)
        self.assertIn("[AI][TC-LOGIN-000001]", exported_titles(exported.data)[0])

        data["test_cases"][0]["title"] = "edited in review page"
        with projection.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
        self.assertEqual(client.post("/api/export/xmind", json={"all": True}).status_code, 400)

        data["test_cases"][0]["title"] = "正确凭据登录"
        with projection.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
        formal.write_text("case_set_id: CASESET-LOGIN\ncases: [edited]\n", encoding="utf-8")
        self.assertEqual(client.post("/api/export/xmind", json={"all": True}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
