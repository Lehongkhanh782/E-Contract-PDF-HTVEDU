"""Dựng hợp đồng: JSON có cấu trúc -> hai tệp Word -> một tệp PDF.

Chế độ phát hành đọc từ config/business_rules.json, khoá document_issue.mode:

- demo: mỗi trang in dòng cảnh báo, số hợp đồng có tiền tố DEMO.
- official: bản ký thật, không phủ gì lên trang.

Từ 20/09/2026 chạy ở chế độ official, sau khi kế toán xác nhận mức lương
từng vị trí, tỷ lệ bảo hiểm và công đoàn, cách tính thuế thu nhập cá nhân.
Số hợp đồng đánh theo mã nhân viên.

Chương trình này vẫn không có phần đăng nhập, đọc giấy tờ, cơ sở dữ liệu
hay luồng duyệt; những phần đó nằm ở ứng dụng web trong thư mục backend.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from salary_engine import calculate_salary_terms, decimal_input, round_vnd, whole_vnd

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
TOKEN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
ROOT = Path(__file__).resolve().parent


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def replace_span(paragraph, start: int, end: int, value: str):
    """Replace a text span while retaining run formatting outside the span."""
    nodes = paragraph.xpath(".//w:t", namespaces=NS)
    cursor = 0
    overlaps = []
    for node in nodes:
        text = node.text or ""
        node_end = cursor + len(text)
        if node_end > start and cursor < end:
            overlaps.append((node, cursor, text))
        cursor = node_end
    if not overlaps:
        raise ValueError("Replacement span does not overlap any text")
    first = overlaps[0][0]
    for node, offset, original in overlaps:
        left = original[:max(0, start - offset)]
        right = original[max(0, end - offset):] if end < offset + len(original) else ""
        node.text = left + (value if node is first else "") + right
        node.set(XML_SPACE, "preserve")


def resolve(data: dict, dotted: str):
    value = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Thiếu biến {dotted}")
        value = value[part]
    if value is None or not isinstance(value, (str, int)):
        raise ValueError(f"Biến {dotted} chưa có giá trị hiển thị hợp lệ")
    value = str(value)
    if not value.strip():
        raise ValueError(f"Biến {dotted} không được trống")
    if "{{" in value or "}}" in value or any(ord(c) < 32 for c in value):
        raise ValueError(f"Biến {dotted} chứa ký tự không hỗ trợ")
    return value


def render_docx(template: Path, output: Path, context: dict):
    """Literal dotted variables only: no expressions, calls, filters or eval."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(template) as source, ZipFile(output, "w") as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename.startswith("word/") and info.filename.endswith(".xml"):
                root = etree.fromstring(content, parser)
                for paragraph in root.xpath("//w:p", namespaces=NS):
                    text = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
                    for match in reversed(list(TOKEN.finditer(text))):
                        replace_span(paragraph, match.start(), match.end(),
                                     resolve(context, match.group(1)))
                remaining = "".join(root.xpath("//w:t/text()", namespaces=NS))
                if "{{" in remaining or "}}" in remaining:
                    raise ValueError(f"Biến không hợp lệ trong {info.filename}")
                content = etree.tostring(root, xml_declaration=True,
                                         encoding="UTF-8", standalone=True)
            target.writestr(info, content)


def money(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", ".")


CHU_SO = ["không", "một", "hai", "ba", "bốn",
          "năm", "sáu", "bảy", "tám", "chín"]
TEN_NHOM = ["", " nghìn", " triệu", " tỷ"]


def _doc_ba_chu_so(so: int, day_du: bool) -> str:
    """Đọc một nhóm ba chữ số. day_du là True khi nhóm phải đọc cả số 0 đầu."""
    tram, du = divmod(so, 100)
    chuc, donvi = divmod(du, 10)
    phan = []
    if tram > 0 or day_du:
        phan.append(f"{CHU_SO[tram]} trăm")
    if chuc == 0:
        if donvi > 0:
            if tram > 0 or day_du:
                phan.append("linh")
            phan.append(CHU_SO[donvi])
    elif chuc == 1:
        phan.append("mười")
        if donvi == 5:
            phan.append("lăm")
        elif donvi > 0:
            phan.append(CHU_SO[donvi])
    else:
        phan.append(f"{CHU_SO[chuc]} mươi")
        if donvi == 1:
            phan.append("mốt")
        elif donvi == 4:
            phan.append("tư")
        elif donvi == 5:
            phan.append("lăm")
        elif donvi > 0:
            phan.append(CHU_SO[donvi])
    return " ".join(phan)


def doc_so_tien(value) -> str:
    """Đổi số tiền sang chữ tiếng Việt, ví dụ 20000000 -> hai mươi triệu đồng.

    Dùng cho các điều khoản bắt buộc ghi cả số lẫn chữ.
    """
    so = int(Decimal(str(value)))
    if so < 0:
        raise ValueError("Số tiền không được âm")
    if so == 0:
        return "không đồng"
    nhom = []
    con_lai = so
    while con_lai > 0:
        con_lai, du = divmod(con_lai, 1000)
        nhom.append(du)
    if len(nhom) > len(TEN_NHOM):
        raise ValueError("Số tiền vượt phạm vi đã kiểm thử")
    cao_nhat = len(nhom) - 1
    phan = []
    for i in range(cao_nhat, -1, -1):
        if nhom[i] == 0:
            continue
        phan.append(_doc_ba_chu_so(nhom[i], i != cao_nhat) + TEN_NHOM[i])
    return " ".join(phan) + " đồng"


def selected_position(data: dict) -> dict:
    position_id = data.get("job", {}).get("position_id")
    roles = load_json(ROOT / "config/business_rules.json")["positions"]
    matches = [role for role in roles if role["position_id"] == position_id]
    if len(matches) != 1:
        raise ValueError("Chọn vị trí đã cấu hình; không tự đoán lương cơ bản")
    return matches[0]


def can_thoa_thuan(data: dict) -> bool:
    """Vị trí này có phải ký thỏa thuận trách nhiệm không.

    Chỉ các vị trí trực tiếp dạy và trông trẻ mới kèm tờ này. Cấu hình
    thiếu cờ thì dừng lại, không tự đoán.
    """
    position = selected_position(data)
    if "requires_responsibility_agreement" not in position:
        raise ValueError(
            f"Vị trí {position['position_id']} chưa khai "
            "requires_responsibility_agreement trong business_rules.json"
        )
    return bool(position["requires_responsibility_agreement"])


def thue_theo_nguong(policy: dict):
    """Trả về hàm tính thuế thu nhập cá nhân khấu trừ theo mức Gross.

    Kế toán chốt: thu nhập tới ngưỡng thì không khấu trừ; phần vượt ngưỡng
    chịu thuế theo tỷ lệ. Hàm phải nhận Gross làm tham số chứ không tính
    sẵn một lần, vì phép dò Net-sang-Gross tính lại khấu trừ ở từng mức
    Gross nó thử.
    """
    cau_hinh = policy.get("pit")
    if not cau_hinh:
        raise ValueError("Chính sách chưa khai cách tính thuế thu nhập cá nhân")
    nguong = whole_vnd(cau_hinh.get("threshold"), "pit.threshold")
    ty_le = decimal_input(cau_hinh.get("rate"), "pit.rate")
    if ty_le > 1:
        raise ValueError("Tỷ lệ thuế phải nằm trong khoảng 0 đến 1")

    def tinh(gross):
        if gross <= nguong:
            return round_vnd(gross * 0)
        return round_vnd((gross - nguong) * ty_le)

    return tinh


def calculate_example(data: dict, policy: dict) -> dict:
    """Gross/Net demo with explicitly supplied fixed example deductions."""
    if policy.get("status") != "example_only":
        raise ValueError("Prototype chỉ sử dụng chính sách minh họa")
    if policy.get("deduction_model") != "explicit_fixed_amounts_example_only":
        raise ValueError("Cần bộ tính khấu trừ theo Gross đã cấu hình")
    if policy.get("residual_allocation") != "position_allowance_example_only":
        raise ValueError("Chưa xác định cách phân bổ phần thu nhập ngoài lương cơ bản")
    compensation = data["compensation"]
    if "base_wage" in compensation or "position_allowance" in compensation:
        raise ValueError("Dùng position_id, salary_mode và salary_amount theo schema 1.2")
    if compensation.get("pit_withheld") not in (None, ""):
        raise ValueError("Thuế thu nhập cá nhân nay do hệ thống tự tính, "
                         "không nhận số nhập tay")
    base = selected_position(data)["base_wage"]
    insurance_base = whole_vnd(compensation.get("insurance_base"), "insurance_base")
    employer_union_base = whole_vnd(compensation.get("employer_union_base"), "employer_union_base")
    employee_union_base = whole_vnd(compensation.get("employee_union_base"), "employee_union_base")
    rates = {key: decimal_input(value, key) for key, value in policy["rates"].items()}
    if any(rate > 1 for rate in rates.values()):
        raise ValueError("Tỷ lệ minh họa phải nằm trong khoảng 0 đến 1")
    tinh_thue = thue_theo_nguong(policy)
    # Các khoản bảo hiểm và công đoàn tính trên căn cứ đóng nên không đổi
    # theo Gross; riêng thuế thì có, nên phải tính lại ở từng mức Gross mà
    # phép dò Net-sang-Gross thử qua.
    co_dinh = {
        "employer_insurance": round_vnd(insurance_base * rates["employer_insurance"]),
        "employer_union": round_vnd(employer_union_base * rates["employer_union"]),
        "employee_insurance": round_vnd(insurance_base * rates["employee_insurance"]),
        "employee_union": round_vnd(employee_union_base * rates["employee_union"]),
    }
    result = calculate_salary_terms(
        base, compensation.get("salary_mode"), compensation.get("salary_amount"),
        lambda gross: {**co_dinh, "pit_withheld": tinh_thue(gross)})
    # Only this explicit example policy puts the residual into the source
    # template's single allowance line. Production allocation is still pending.
    result["position_allowance"] = result.pop("income_above_base")
    return {key: str(value) for key, value in result.items()}


def date_short(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def date_long(value: str) -> str:
    d = date.fromisoformat(value)
    return f"{d.day:02d} tháng {d.month:02d} năm {d.year}"


def page_count_label(count: int) -> str:
    names = {1: "một", 2: "hai", 3: "ba", 4: "bốn", 5: "năm",
             6: "sáu", 7: "bảy", 8: "tám", 9: "chín", 10: "mười"}
    if count not in names:
        raise ValueError("Thỏa thuận vượt phạm vi số trang đã kiểm thử")
    return f"{count:02d} ({names[count]})"


def ban_thu_nghiem() -> bool:
    """Bản in có phải bản thử nghiệm không, đọc từ cấu hình nghiệp vụ.

    Để trong cấu hình chứ không để trong biến môi trường, vì đây là quyết
    định phải nhìn thấy được trong Git: chuyển sang bản ký thật là chuyện
    cần có người rà lại, không phải chuyện gõ một dòng trên máy chủ.
    """
    cach = load_json(ROOT / "config/business_rules.json").get("document_issue")
    if not cach or cach.get("mode") not in ("demo", "official"):
        raise ValueError(
            "Cấu hình chưa khai document_issue.mode là demo hay official"
        )
    return cach["mode"] == "demo"


def so_van_ban(ma_co_so: str, loai: str, ma_nhan_vien: str) -> str:
    """Số hợp đồng đánh theo mã nhân viên, theo xác nhận của kế toán.

    Giữ nguyên hai đoạn HDLD và TT vì bài kiểm tra bố cục in hai mặt dựa
    vào chúng để biết trang nào mở đầu phần nào.
    """
    ma_nhan_vien = (ma_nhan_vien or "").strip()
    if not ma_nhan_vien:
        raise ValueError("Thiếu mã nhân viên nên không đánh được số hợp đồng")
    so = f"{ma_co_so}/{loai}/{ma_nhan_vien}"
    return f"DEMO/{so}" if ban_thu_nghiem() else so


def _don_vi(unit_id: str) -> dict:
    units = load_json(ROOT / "config/units.json")["units"]
    chon = [unit for unit in units if unit["unit_id"] == unit_id]
    if len(chon) != 1:
        raise ValueError("Đơn vị không có trong cấu hình")
    return copy.deepcopy(chon[0])


def so_thang(bat_dau: date, ket_thuc: date) -> int:
    """Số tháng giữa hai mốc, tính cả ngày kết thúc.

    Cộng một ngày vào mốc cuối trước khi đếm, để mốc rơi đúng ngày cuối
    tháng ra số tháng tròn thay vì thiếu một ngày.
    """
    sau = ket_thuc + timedelta(days=1)
    thang = (sau.year - bat_dau.year) * 12 + sau.month - bat_dau.month
    if sau.day < bat_dau.day:
        thang -= 1
    return thang


def build_probation_context(unit_id: str, data: dict) -> tuple[dict, dict]:
    """Dựng dữ liệu cho hợp đồng thử việc.

    Thử việc chỉ có một tờ hợp đồng: không phụ lục lương, không thỏa thuận
    trách nhiệm, và không khấu trừ bảo hiểm hay công đoàn — nhà trường xác
    nhận trong thời gian thử việc chưa hưởng các chế độ đó. Vì vậy hàm này
    không đi qua bộ tính lương của hợp đồng chính thức.
    """
    unit = _don_vi(unit_id)
    thu_viec = data["probation"]
    bat_dau = date.fromisoformat(thu_viec["start_date"])
    ket_thuc = date.fromisoformat(thu_viec["end_date"])
    if ket_thuc < bat_dau:
        raise ValueError("Ngày kết thúc thử việc trước ngày bắt đầu")

    luong_chinh_thuc = whole_vnd(thu_viec.get("full_gross"), "probation.full_gross")
    if luong_chinh_thuc <= 0:
        raise ValueError("Lương chính thức phải lớn hơn 0")
    ty_le = decimal_input(thu_viec.get("rate_percent"), "probation.rate_percent")
    if not 0 < ty_le <= 100:
        raise ValueError("Tỷ lệ lương thử việc phải trong khoảng 0 đến 100")
    luong_thu_viec = round_vnd(luong_chinh_thuc * ty_le / 100)

    thang = so_thang(bat_dau, ket_thuc)
    ket_qua = {
        "full_gross": str(luong_chinh_thuc),
        "rate_percent": str(ty_le.normalize()),
        "probation_salary": str(luong_thu_viec),
        "months": str(thang),
    }
    position = selected_position(data)
    context = {
        "employer": {
            **unit,
            "workplace_institution_upper":
                unit["workplace_institution_name"].upper(),
        },
        "employee": {
            **copy.deepcopy(data["employee"]),
            # Ngày trong hợp đồng viết dd/mm/yyyy, không phải dạng máy.
            "birth_date": date_short(data["employee"]["birth_date"]),
            "identity_issue_date":
                date_short(data["employee"]["identity_issue_date"]),
        },
        "job": {
            "title": position["title"],
            "role_label": position["role_label"],
            "department": data["job"].get("department") or position["title"],
            "supervisor_name": data["job"].get("supervisor_name") or "",
        },
        "payment": copy.deepcopy(data["payment"]),
        "signing": {"date_long": date_long(data["signing_date"])},
        "contract": {
            "number": so_van_ban(unit["code"], "HDTV",
                                 data["employee"].get("code")),
        },
        "probation": {
            "start_date": date_short(thu_viec["start_date"]),
            "end_date": date_short(thu_viec["end_date"]),
            "term_text": f"{thang} tháng",
            "rate_percent": ket_qua["rate_percent"],
            "work_hours": thu_viec["work_hours"],
            "rest_hours": thu_viec["rest_hours"],
        },
        "display": {
            "full_gross": money(luong_chinh_thuc),
            "probation_salary": money(luong_thu_viec),
        },
    }
    return context, ket_qua


def build_context(unit_id: str, data: dict, policy: dict, agreement_pages=3):
    if data.get("demo_only") is not True:
        raise ValueError("Chỉ hỗ trợ dữ liệu minh họa demo_only=true")
    units = load_json(ROOT / "config/units.json")["units"]
    choices = [unit for unit in units if unit["unit_id"] == unit_id]
    if len(choices) != 1:
        raise ValueError("Đơn vị không có trong cấu hình")
    unit = copy.deepcopy(choices[0])
    contract = data["contract"]
    signing_date = data.get("signing_date")
    if not isinstance(signing_date, str) or not signing_date.strip():
        raise ValueError("Phải nhập ngày ký; đây cũng là ngày hiệu lực hợp đồng")
    if "start_date" in contract:
        raise ValueError("Chỉ nhập signing_date; không nhập contract.start_date riêng")
    start = date.fromisoformat(signing_date)
    end = date.fromisoformat(contract["end_date"])
    if end < start:
        raise ValueError("Ngày kết thúc trước ngày bắt đầu")
    result = calculate_example(data, policy)
    position = selected_position(data)
    muc_boi_thuong = unit.get("liability_amount")
    if not muc_boi_thuong or not str(muc_boi_thuong).isdigit():
        raise ValueError(
            f"Đơn vị {unit_id} chưa cấu hình liability_amount; "
            "không tự đoán mức bồi thường"
        )
    context = {
        "employer": unit,
        "employee": copy.deepcopy(data["employee"]),
        "job": {"title": position["title"], "role_label": position["role_label"]},
        "work_schedule": copy.deepcopy(data["work_schedule"]),
        "payment": copy.deepcopy(data["payment"]),
        "contract": {
            "number": so_van_ban(unit["code"], "HDLD",
                                 data["employee"].get("code")),
            "type_term_text": contract["type_term_text"],
            "start_date": date_short(signing_date),
            "end_date": date_short(contract["end_date"]),
        },
        "signing": {"date_long": date_long(signing_date)},
        "salary": {
            "effective_from": date_short(data["salary_period"]["effective_from"]),
            "effective_to": date_short(data["salary_period"]["effective_to"]),
        },
        "responsibility": {
            "number": so_van_ban(unit["code"], "TT",
                                 data["employee"].get("code")),
            "commitment_from": date_short(data["responsibility"]["commitment_from"]),
            "commitment_to": date_short(data["responsibility"]["commitment_to"]),
            "liability_from": date_short(data["responsibility"]["liability_from"]),
            "liability_to": date_short(data["responsibility"]["liability_to"]),
            # Mức bồi thường khác nhau theo đơn vị, lấy từ cấu hình chứ không
            # ghi cứng trong mẫu Word.
            "liability_amount": money(Decimal(muc_boi_thuong)),
            "liability_amount_words": doc_so_tien(muc_boi_thuong),
            "page_count_label": page_count_label(agreement_pages),
        },
        "display": {key: money(Decimal(value)) for key, value in result.items()},
    }
    context["employee"]["birth_date"] = date_short(data["employee"]["birth_date"])
    context["employee"]["identity_issue_date"] = date_short(data["employee"]["identity_issue_date"])
    return context, result


def convert_to_pdf(docx: Path, destination: Path, soffice: str) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile:
        command = [
            soffice, "--headless",
            f"-env:UserInstallation={Path(profile).resolve().as_uri()}",
            "--convert-to", "pdf:writer_pdf_Export",
            "--outdir", str(destination.resolve()), str(docx.resolve()),
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=120)
    pdf = destination / (docx.stem + ".pdf")
    if result.returncode != 0 or not pdf.exists() or pdf.stat().st_size == 0:
        raise RuntimeError("Không chuyển được Word sang PDF; kiểm tra LibreOffice và font")
    return pdf


# Dòng chữ nhận ra trang đầu của phụ lục lương. Hợp đồng và phụ lục nằm
# chung một file Word nên phải tách theo nội dung để chèn được trang trắng.
DAU_HIEU_PHU_LUC = "PHỤ LỤC HỢP ĐỒNG"


def tach_hop_dong_va_phu_luc(path: Path) -> tuple[list[int], list[int]]:
    """Tìm ranh giới giữa hợp đồng và phụ lục trong cùng một PDF."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    vi_tri = [i for i, page in enumerate(reader.pages)
              if DAU_HIEU_PHU_LUC in (page.extract_text() or "")]
    if len(vi_tri) != 1:
        raise ValueError(
            f"Cần đúng một trang mở đầu phụ lục có chữ {DAU_HIEU_PHU_LUC!r}; "
            f"tìm thấy {len(vi_tri)}. Kiểm tra lại mẫu Word."
        )
    bat_dau = vi_tri[0]
    if bat_dau == 0:
        raise ValueError("Phụ lục nằm ngay trang đầu; mẫu hợp đồng có vấn đề")
    return list(range(bat_dau)), list(range(bat_dau, len(reader.pages)))


def _dong_danh_dau(overlay, width, height):
    """In dòng cảnh báo ở đầu trang. Bản ký thật thì không in gì."""
    if not ban_thu_nghiem():
        return
    overlay.setFillColorRGB(0.68, 0.05, 0.06)
    overlay.setFont("DemoNotice", 8)
    overlay.drawCentredString(width / 2, height - 16,
                             "BẢN THỬ NGHIỆM - DỮ LIỆU GIẢ - CHƯA DÙNG KÝ")


def _trang_de_trong(width: float, height: float):
    """Trang chèn thêm để phần sau bắt đầu ở mặt trước của một tờ mới.

    Có ghi chú mờ ở giữa để người nhận biết là cố ý bỏ trống, không phải
    máy in bị lỗi.
    """
    from pypdf import PdfReader
    from reportlab.pdfgen import canvas

    stream = io.BytesIO()
    trang = canvas.Canvas(stream, pagesize=(width, height))
    _dong_danh_dau(trang, width, height)
    trang.setFillColorRGB(0.6, 0.6, 0.6)
    trang.setFont("DemoNotice", 9)
    trang.drawCentredString(width / 2, height / 2, "(Trang này để trống)")
    trang.save()
    return PdfReader(io.BytesIO(stream.getvalue())).pages[0]


def merge_demo_pdf(paths: list[Path], output: Path, font_path: Path,
                   mot_tap: bool = False):
    """Ghép thành một PDF, chèn trang trắng để in hai mặt tách tờ được.

    Hợp đồng, phụ lục lương và thỏa thuận được bấm thành ba tập riêng, nên
    mỗi phần phải bắt đầu ở mặt trước của một tờ mới. Khi in hai mặt, mặt
    trước luôn là trang lẻ, vì vậy phần nào kết thúc ở trang lẻ sẽ được
    chèn thêm một trang trắng.

    mot_tap=True dành cho hợp đồng thử việc: chỉ một tập, không phụ lục,
    nên không tách và không chèn trang trắng nào.
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont("DemoNotice", str(font_path)))
    if not 1 <= len(paths) <= 2:
        raise ValueError("Cần một file hợp đồng, kèm hoặc không kèm thỏa thuận")
    contract_pdf = paths[0]

    if mot_tap:
        if len(paths) != 1:
            raise ValueError("Bộ một tập chỉ nhận đúng một file")
        phan = [("Hợp đồng thử việc", contract_pdf,
                 list(range(len(PdfReader(contract_pdf).pages))))]
    else:
        trang_hop_dong, trang_phu_luc = tach_hop_dong_va_phu_luc(contract_pdf)
        phan = [
            ("Hợp đồng lao động", contract_pdf, trang_hop_dong),
            ("Phụ lục lương", contract_pdf, trang_phu_luc),
        ]
    # Vị trí không phải ký thỏa thuận thì bộ hồ sơ chỉ có hai phần.
    # Bộ một tập đã chặn trường hợp hai file ở trên.
    if len(paths) == 2:
        agreement_pdf = paths[1]
        phan.append(("Thỏa thuận trách nhiệm", agreement_pdf,
                     list(range(len(PdfReader(agreement_pdf).pages)))))

    writer = PdfWriter()
    moc = []
    for thu_tu, (ten, nguon, chi_so) in enumerate(phan):
        reader = PdfReader(nguon)
        moc.append((ten, len(writer.pages)))
        width = height = None
        for i in chi_so:
            page = reader.pages[i]
            content = (page.extract_text() or "").strip()
            if not content or content.isdigit():
                raise ValueError(
                    "Phát hiện trang chỉ trống hoặc chỉ có số trang; kiểm tra mẫu"
                )
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            # Bản ký thật không phủ gì lên trang. Không được dựng trang phủ
            # rỗng rồi ghép: canvas không vẽ gì thì không sinh ra trang nào,
            # và việc ghép sẽ hỏng.
            if ban_thu_nghiem():
                stream = io.BytesIO()
                overlay = canvas.Canvas(stream, pagesize=(width, height))
                _dong_danh_dau(overlay, width, height)
                overlay.save()
                page.merge_page(PdfReader(io.BytesIO(stream.getvalue())).pages[0])
            writer.add_page(page)
        # Phần cuối không cần đệm: máy in tự để trống mặt sau tờ cuối.
        con_phan_sau = thu_tu < len(phan) - 1
        if con_phan_sau and len(writer.pages) % 2 == 1:
            writer.add_page(_trang_de_trong(width, height))

    for ten, vi_tri in moc:
        writer.add_outline_item(ten, vi_tri)
    writer.add_metadata({"/Title": "Bộ hợp đồng thử nghiệm",
                         "/Subject": "Dữ liệu giả; chưa dùng ký",
                         "/Author": ""})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit", default="dai_duong_xanh")
    parser.add_argument("--input", type=Path, default=ROOT / "examples/employee_demo.json")
    parser.add_argument("--output", type=Path, default=ROOT / "out/Bo_hop_dong_thu.pdf")
    parser.add_argument("--soffice", default=shutil.which("soffice") or shutil.which("libreoffice"))
    parser.add_argument("--font", type=Path,
                        default=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    parser.add_argument("--docx-only-dir", type=Path,
                        help="For developer QA; files remain clearly named DEMO")
    parser.add_argument("--calculate-only", action="store_true",
                        help="Print example calculation without Word/PDF conversion")
    args = parser.parse_args()
    policy = load_json(ROOT / "config/salary_policy_example.json")
    data = load_json(args.input)
    context, result = build_context(args.unit, data, policy)
    if args.calculate_only:
        print(json.dumps({"demo_only": True,
                          "salary_mode": data["compensation"]["salary_mode"],
                          "salary_amount": data["compensation"]["salary_amount"],
                          "calculation": result}, ensure_ascii=False, indent=2))
        return
    templates = [ROOT / "templates/Hop_dong_va_phu_luc_template.docx",
                 ROOT / "templates/Thoa_thuan_trach_nhiem_template.docx"]
    if args.docx_only_dir:
        names = ["DEMO_Hop_dong_va_phu_luc.docx", "DEMO_Thoa_thuan.docx"]
        for template, name in zip(templates, names):
            render_docx(template, args.docx_only_dir / name, context)
        write_json(args.docx_only_dir / "calculation_demo.json", result)
        print("Đã tạo DOCX minh họa cho kiểm tra kỹ thuật; chưa dùng ký.")
        return
    if not args.soffice:
        raise SystemExit("Cần cài LibreOffice hoặc truyền --soffice")
    if not args.font.exists():
        raise SystemExit("Truyền --font tới file TTF hỗ trợ tiếng Việt")
    from pypdf import PdfReader
    kem_thoa_thuan = can_thoa_thuan(data)
    with tempfile.TemporaryDirectory(prefix="contract_demo_") as folder:
        work = Path(folder)
        contract_docx = work / "DEMO_Hop_dong_va_phu_luc.docx"
        agreement_docx = work / "DEMO_Thoa_thuan.docx"
        render_docx(templates[0], contract_docx, context)
        contract_pdf = convert_to_pdf(contract_docx, work / "pdf", args.soffice)
        bo_file = [contract_pdf]
        if kem_thoa_thuan:
            for _ in range(3):
                render_docx(templates[1], agreement_docx, context)
                agreement_pdf = convert_to_pdf(agreement_docx, work / "pdf", args.soffice)
                actual = len(PdfReader(agreement_pdf).pages)
                if context["responsibility"]["page_count_label"] == page_count_label(actual):
                    break
                context["responsibility"]["page_count_label"] = page_count_label(actual)
            else:
                raise RuntimeError("Số trang thỏa thuận chưa ổn định")
            bo_file.append(agreement_pdf)
        merge_demo_pdf(bo_file, args.output, args.font)
    write_json(args.output.with_suffix(".calculation.json"), {
        "demo_only": True, "unit_id": args.unit, "calculation": result,
        "position_id": data["job"]["position_id"],
        "salary_mode": data["compensation"]["salary_mode"],
        "salary_amount": data["compensation"]["salary_amount"],
        "signing_and_effective_date": data["signing_date"],
        "includes_responsibility_agreement": kem_thoa_thuan,
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "policy_status": policy["status"],
    })
    print(f"Đã tạo PDF thử nghiệm: {args.output}")


if __name__ == "__main__":
    main()
