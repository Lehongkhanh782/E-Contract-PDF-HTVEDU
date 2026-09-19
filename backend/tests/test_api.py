"""Kiểm thử API: cấu hình, phép tính và các lỗi đầu vào quan trọng."""
from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import KIT_DIR  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def sample_request() -> dict:
    """Lấy hồ sơ giả của contract_kit và đưa về định dạng của API."""
    data = json.loads(
        (KIT_DIR / "examples/employee_demo.json").read_text(encoding="utf-8")
    )
    for key in ("schema_version", "demo_only", "assumptions"):
        data.pop(key, None)
    return data


class TestConfigEndpoints(unittest.TestCase):
    def test_health(self):
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["demo_only"])

    def test_units_lists_four_configured_units(self):
        body = client.get("/api/units").json()
        ids = [unit["unit_id"] for unit in body["units"]]
        self.assertEqual(
            ids, ["vuon_sang_tao", "victoria", "gau_panda", "dai_duong_xanh"]
        )

    def test_units_do_not_claim_production_readiness(self):
        body = client.get("/api/units").json()
        self.assertTrue(all(not unit["production_ready"] for unit in body["units"]))

    def test_dai_duong_xanh_uses_confirmed_tax_code(self):
        body = client.get("/api/units").json()
        unit = next(u for u in body["units"] if u["unit_id"] == "dai_duong_xanh")
        self.assertEqual(unit["tax_code"], "0318961728-002")

    def test_positions_expose_confirmed_base_wages(self):
        body = client.get("/api/positions").json()
        wages = {p["position_id"]: p["base_wage"] for p in body["positions"]}
        self.assertEqual(wages["principal"], "7000000")
        self.assertEqual(wages["english_teacher"], "5310000")
        self.assertEqual(len(wages), 5)

    def test_defaults_are_marked_pending_review(self):
        body = client.get("/api/defaults").json()
        self.assertEqual(body["status"], "example_values_pending_review")
        self.assertIn("weekday_morning", body["work_schedule"])


class TestPreview(unittest.TestCase):
    def test_gross_matches_supplied_example(self):
        response = client.post("/api/preview", json=sample_request())
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["calculation"]["net_income"], "5389350")
        self.assertEqual(body["calculation"]["gross_income"], "6000000")
        self.assertEqual(body["calculation"]["base_wage"], "5310000")
        self.assertEqual(body["calculation"]["position_allowance"], "690000")

    def test_net_mode_finds_matching_gross(self):
        payload = sample_request()
        payload["compensation"]["salary_mode"] = "net"
        payload["compensation"]["salary_amount"] = "6000000"
        body = client.post("/api/preview", json=payload).json()
        self.assertEqual(body["calculation"]["gross_income"], "6610650")
        self.assertEqual(body["calculation"]["net_income"], "6000000")

    def test_preview_reports_policy_is_example_only(self):
        body = client.post("/api/preview", json=sample_request()).json()
        self.assertEqual(body["policy_status"], "example_only")
        self.assertTrue(body["demo_only"])


class TestInputRules(unittest.TestCase):
    def test_unknown_unit_is_rejected(self):
        payload = sample_request()
        payload["unit_id"] = "khong_ton_tai"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 400)

    def test_unknown_position_is_rejected(self):
        payload = sample_request()
        payload["job"]["position_id"] = "khong_ton_tai"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 400)

    def test_end_date_before_signing_date_is_rejected(self):
        payload = sample_request()
        payload["contract"]["end_date"] = "2026-07-01"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 400)

    def test_missing_signing_date_is_rejected(self):
        payload = sample_request()
        payload.pop("signing_date")
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_separate_contract_start_date_is_rejected(self):
        payload = sample_request()
        payload["contract"]["start_date"] = "2026-08-01"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_legacy_base_wage_input_is_rejected(self):
        payload = sample_request()
        payload["compensation"]["base_wage"] = "5310000"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_invalid_salary_mode_is_rejected(self):
        payload = sample_request()
        payload["compensation"]["salary_mode"] = "khac"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_zero_salary_is_rejected(self):
        payload = sample_request()
        payload["compensation"]["salary_amount"] = "0"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_non_numeric_salary_is_rejected(self):
        payload = sample_request()
        payload["compensation"]["salary_amount"] = "6.000.000"
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_blank_employee_name_is_rejected(self):
        payload = sample_request()
        payload["employee"]["full_name"] = ""
        self.assertEqual(client.post("/api/preview", json=payload).status_code, 422)

    def test_each_configured_unit_can_be_calculated(self):
        base = sample_request()
        for unit_id in ("vuon_sang_tao", "victoria", "gau_panda", "dai_duong_xanh"):
            payload = deepcopy(base)
            payload["unit_id"] = unit_id
            with self.subTest(unit=unit_id):
                response = client.post("/api/preview", json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json()["calculation"]["net_income"], "5389350"
                )


if __name__ == "__main__":
    unittest.main()
