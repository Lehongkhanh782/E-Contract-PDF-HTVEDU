"""Các endpoint của ứng dụng."""
from __future__ import annotations

import json
import shutil
import tempfile
import unicodedata
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from app import config
from app.schemas import ContractRequest
from app.services import documents

router = APIRouter(prefix="/api")

DEMO_NOTICE = (
    "Bản thử nghiệm. Mọi PDF đều mang dấu DỮ LIỆU GIẢ - CHƯA DÙNG KÝ "
    "và không dùng để ký thật."
)


def _ascii_filename(name: str) -> str:
    """Tên file cho header Content-Disposition, bỏ dấu tiếng Việt."""
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stripped)
    return safe.strip("_") or "hop_dong"


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_only": True}


@router.get("/units")
def list_units() -> dict:
    """4 đơn vị đã cấu hình. Chỉ trả phần cần cho giao diện."""
    return {
        "units": [
            {
                "unit_id": unit["unit_id"],
                "code": unit["code"],
                "display_name": unit["display_name"],
                "legal_name": unit["legal_name"],
                "tax_code": unit["tax_code"],
                "address": unit["address"],
                "signatory_display": unit["signatory_display"],
                "signatory_title": unit["signatory_title"],
                "production_ready": unit["production_ready"],
            }
            for unit in config.units()
        ],
        "notice": DEMO_NOTICE,
    }


@router.get("/positions")
def list_positions() -> dict:
    """5 vị trí và mức lương cơ bản đã được xác nhận."""
    rules = config.business_rules()
    return {
        "positions": config.positions(),
        "salary_modes": rules["salary_input"]["options"],
        "deduction_policy_status": rules["salary_input"]["deduction_policy_status"],
    }


@router.get("/defaults")
def form_defaults() -> dict:
    """Giá trị gợi ý cho các ô dài, lấy từ hồ sơ mẫu để nhân sự đỡ gõ lại.

    Đây là gợi ý điền nhanh, không phải điều khoản đã duyệt cho mọi vị trí.
    """
    data = json.loads(
        (config.KIT_DIR / "examples/employee_demo.json").read_text(encoding="utf-8")
    )
    return {
        "work_schedule": data["work_schedule"],
        "payment": data["payment"],
        "contract": {"type_term_text": data["contract"]["type_term_text"]},
        "compensation": {
            "pit_withheld": data["compensation"]["pit_withheld"],
            "salary_mode": data["compensation"]["salary_mode"],
        },
        "status": "example_values_pending_review",
    }


@router.post("/preview")
def preview(request: ContractRequest) -> JSONResponse:
    """Tính tiền và trả kết quả, không tạo file. Dùng cho bảng xem trước."""
    try:
        result = documents.calculate(request.unit_id, request.to_kit_payload())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse(
        {
            "demo_only": True,
            "unit_id": request.unit_id,
            "calculation": result,
            "policy_status": config.salary_policy()["status"],
            "notice": DEMO_NOTICE,
        }
    )


@router.post("/generate")
def generate(request: ContractRequest) -> FileResponse:
    """Tạo PDF gồm hợp đồng, phụ lục lương và thỏa thuận trách nhiệm."""
    folder = Path(tempfile.mkdtemp(prefix="econtract_out_"))
    target = folder / "Bo_hop_dong_thu_nghiem.pdf"

    def cleanup() -> None:
        shutil.rmtree(folder, ignore_errors=True)

    try:
        meta = documents.build_pdf(request.unit_id, request.to_kit_payload(), target)
    except ValueError as error:
        cleanup()
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        cleanup()
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception:
        cleanup()
        raise

    name = _ascii_filename(f"DEMO_{request.employee.code}_{request.unit_id}") + ".pdf"
    return FileResponse(
        target,
        media_type="application/pdf",
        filename=name,
        headers={
            "X-Demo-Only": "true",
            "X-Calculation-Sha256": meta["sha256"],
        },
        background=BackgroundTask(cleanup),
    )
