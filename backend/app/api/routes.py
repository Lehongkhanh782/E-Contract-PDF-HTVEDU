"""Các endpoint của ứng dụng."""
from __future__ import annotations

import json
import logging
import shutil
import tempfile
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from app import config
from app.auth import User
from app.deps import current_user, require_unit
from app.schemas import ContractRequest, SalaryRequest
from app.services import documents, ocr, sheets

logger = logging.getLogger("econtract.ocr")

router = APIRouter(prefix="/api")


def _thong_bao_phat_hanh() -> str:
    """Câu nhắc hiện trên đầu trang, bám theo chế độ phát hành đang đặt."""
    if documents.ban_thu_nghiem():
        return ("Bản thử nghiệm. Mọi PDF đều mang dấu DỮ LIỆU GIẢ - CHƯA "
                "DÙNG KÝ và không dùng để ký thật.")
    return ("Bản ký thật. Mức lương, tỷ lệ bảo hiểm và cách tính thuế đã "
            "được kế toán xác nhận ngày 20/09/2026. Vẫn phải đọc lại hợp "
            "đồng trước khi in.")


def _ascii_filename(name: str) -> str:
    """Tên file cho header Content-Disposition, bỏ dấu tiếng Việt."""
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stripped)
    return safe.strip("_") or "hop_dong"


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_only": documents.ban_thu_nghiem()}


@router.get("/units")
def list_units(user: User = Depends(current_user)) -> dict:
    """Các đơn vị mà tài khoản này được phép dùng."""
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
            if user.may_use(unit["unit_id"])
        ],
        "notice": _thong_bao_phat_hanh(),
    }


@router.get("/positions")
def list_positions(_: User = Depends(current_user)) -> dict:
    """5 vị trí và mức lương cơ bản đã được xác nhận."""
    rules = config.business_rules()
    return {
        "positions": config.positions(),
        "salary_modes": rules["salary_input"]["options"],
        "deduction_policy_status": rules["salary_input"]["deduction_policy_status"],
    }


@router.get("/defaults")
def form_defaults(_: User = Depends(current_user)) -> dict:
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
            "salary_mode": data["compensation"]["salary_mode"],
        },
        "status": "example_values_pending_review",
    }


@router.get("/ocr/status")
def ocr_status(_: User = Depends(current_user)) -> dict:
    """Máy chủ có đọc được ảnh giấy tờ không."""
    return {
        "available": ocr.san_sang(),
        "pdf": ocr.ho_tro_pdf(),
        "fields": ocr.TRUONG,
        "max_bytes": ocr.GIOI_HAN_BYTE,
        "max_pdf_pages": ocr.SO_TRANG_TOI_DA,
        "max_files": ocr.SO_TEP_TOI_DA,
        "note": (
            "Kết quả chỉ là gợi ý để điền nhanh. Nhân sự phải đọc lại từng ô."
        ),
    }


@router.post("/ocr")
async def ocr_giay_to(
    anh: list[UploadFile] = File(...),
    _: User = Depends(current_user),
) -> JSONResponse:
    """Đọc một đến ba tệp giấy tờ và trả về các trường gợi ý đã gộp.

    Tệp chỉ nằm trong bộ nhớ và thư mục tạm, không được lưu lại.
    """
    if len(anh) > ocr.SO_TEP_TOI_DA:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ nhận tối đa {ocr.SO_TEP_TOI_DA} tệp một lần.",
        )

    danh_sach = []
    for tep in anh:
        # Đọc có giới hạn: không nạp cả tệp khổng lồ vào bộ nhớ rồi mới từ chối.
        du_lieu = await tep.read(ocr.GIOI_HAN_BYTE + 1)
        if len(du_lieu) > ocr.GIOI_HAN_BYTE:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Tệp {tep.filename or ''} lớn hơn "
                    f"{ocr.GIOI_HAN_BYTE // (1024 * 1024)} MB. "
                    "Chụp lại hoặc giảm kích thước."
                ),
            )
        danh_sach.append(du_lieu)

    try:
        ket_qua = ocr.gop_nhieu_tep(danh_sach)
    except ocr.AnhKhongHopLe as loi:
        raise HTTPException(status_code=400, detail=str(loi)) from loi
    except ocr.OcrKhongSanSang as loi:
        raise HTTPException(status_code=503, detail=str(loi)) from loi
    except RuntimeError as loi:
        raise HTTPException(status_code=503, detail=str(loi)) from loi
    except Exception as loi:
        # Không để lọt lỗi lạ thành 500 không lời giải thích. Chi tiết ghi
        # vào log của máy chủ, người dùng nhận câu tiếng Việt kèm hướng xử lý.
        logger.exception("Lỗi ngoài dự tính khi đọc giấy tờ")
        raise HTTPException(
            status_code=503,
            detail=(
                "Máy chủ không xử lý được tệp này. Thử chụp thẳng thẻ bằng "
                "điện thoại thay vì tải bản quét, hoặc nhập tay các ô bên dưới."
            ),
        ) from loi

    return JSONResponse(ket_qua)


@router.get("/sheets/status")
def sheets_status(_: User = Depends(current_user)) -> dict:
    """Tình trạng kết nối Google Sheet, kèm chẩn đoán để dò lỗi cấu hình."""
    if not sheets.da_cau_hinh():
        return {
            "configured": False,
            "note": (
                "Chưa nối Google Sheet. Khai ECONTRACT_GOOGLE_KEY và "
                "ECONTRACT_SHEET_ID trên máy chủ để bật."
            ),
        }

    ket_qua: dict = sheets.chan_doan()
    try:
        ket_qua["tabs"] = sheets.danh_sach_tab()
        du_lieu = sheets.danh_sach_nhan_vien()
        ket_qua.update({
            "connected": True,
            "tab_used": du_lieu["tab"],
            "headers": du_lieu["headers"],
            "columns": du_lieu["columns"],
            "employee_count": len(du_lieu["employees"]),
            # Giá trị thật của các cột phân loại, để đối chiếu với cấu hình
            # cơ sở và vị trí. Không kèm thông tin cá nhân của ai.
            "unit_values": sheets.gia_tri_khac_nhau(
                du_lieu["employees"], "unit"),
            "position_values": sheets.gia_tri_khac_nhau(
                du_lieu["employees"], "position"),
            "status_values": sheets.gia_tri_khac_nhau(
                du_lieu["employees"], "status"),
        })
    except sheets.LoiSheet as loi:
        ket_qua.update({"connected": False, "error": str(loi)})
    return ket_qua


@router.get("/employees")
def employees(refresh: bool = False,
              _: User = Depends(current_user)) -> dict:
    """Danh sách nhân viên đọc từ Google Sheet dùng chung."""
    try:
        du_lieu = sheets.danh_sach_nhan_vien(lam_moi=refresh)
    except sheets.ChuaCauHinh as loi:
        raise HTTPException(status_code=503, detail=str(loi)) from loi
    except sheets.LoiSheet as loi:
        raise HTTPException(status_code=502, detail=str(loi)) from loi
    except Exception as loi:
        logger.exception("Lỗi ngoài dự tính khi đọc Google Sheet")
        raise HTTPException(
            status_code=502,
            detail="Không đọc được Google Sheet. Xem lại cấu hình kết nối.",
        ) from loi
    return {
        "employees": du_lieu["employees"],
        "columns": du_lieu["columns"],
        "cached": du_lieu["cached"],
        "note": (
            "Dữ liệu lấy từ Google Sheet dùng chung. Kiểm tra lại trước khi "
            "tạo hợp đồng."
        ),
    }


@router.post("/salary")
def salary(request: SalaryRequest,
           _: User = Depends(current_user)) -> JSONResponse:
    """Tính lương ngay khi nhân sự đang gõ, chưa cần điền xong hồ sơ."""
    try:
        ket_qua = documents.tinh_luong(request.position_id,
                                       request.to_kit_payload())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({
        "demo_only": documents.ban_thu_nghiem(),
        "calculation": ket_qua,
        "policy_status": config.salary_policy()["status"],
    })


@router.post("/preview")
def preview(request: ContractRequest,
            user: User = Depends(current_user)) -> JSONResponse:
    """Tính tiền và trả kết quả, không tạo file. Dùng cho bảng xem trước."""
    require_unit(user, request.unit_id)
    try:
        result = documents.calculate(request.unit_id, request.to_kit_payload())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse(
        {
            "demo_only": documents.ban_thu_nghiem(),
            "unit_id": request.unit_id,
            "calculation": result,
            "policy_status": config.salary_policy()["status"],
            "notice": _thong_bao_phat_hanh(),
        }
    )


@router.post("/generate")
def generate(request: ContractRequest,
             user: User = Depends(current_user)) -> FileResponse:
    """Tạo PDF gồm hợp đồng, phụ lục lương và thỏa thuận trách nhiệm."""
    require_unit(user, request.unit_id)
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
