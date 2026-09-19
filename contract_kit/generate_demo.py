"""Prototype: structured JSON -> two Word documents -> one watermarked PDF.

This program only makes demonstration documents. It has no production
issuance mode, authentication, OCR, database, contract numbering or legal
approval workflow. Use the application specification for those components.
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
from datetime import date
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
    base = selected_position(data)["base_wage"]
    insurance_base = whole_vnd(compensation.get("insurance_base"), "insurance_base")
    employer_union_base = whole_vnd(compensation.get("employer_union_base"), "employer_union_base")
    employee_union_base = whole_vnd(compensation.get("employee_union_base"), "employee_union_base")
    pit = whole_vnd(compensation.get("pit_withheld"), "pit_withheld")
    rates = {key: decimal_input(value, key) for key, value in policy["rates"].items()}
    if any(rate > 1 for rate in rates.values()):
        raise ValueError("Tỷ lệ minh họa phải nằm trong khoảng 0 đến 1")
    fixed_example = {
        "employer_insurance": round_vnd(insurance_base * rates["employer_insurance"]),
        "employer_union": round_vnd(employer_union_base * rates["employer_union"]),
        "employee_insurance": round_vnd(insurance_base * rates["employee_insurance"]),
        "employee_union": round_vnd(employee_union_base * rates["employee_union"]),
        "pit_withheld": pit,
    }
    result = calculate_salary_terms(
        base, compensation.get("salary_mode"), compensation.get("salary_amount"),
        lambda gross: fixed_example)
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
            "number": f"DEMO/{unit['code']}/HDLD/0001",
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
            "number": f"DEMO/{unit['code']}/TT/0001",
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


def merge_demo_pdf(paths: list[Path], output: Path, font_path: Path):
    """Ghép thành một PDF, chèn trang trắng để in hai mặt tách tờ được.

    Hợp đồng, phụ lục lương và thỏa thuận được bấm thành ba tập riêng, nên
    mỗi phần phải bắt đầu ở mặt trước của một tờ mới. Khi in hai mặt, mặt
    trước luôn là trang lẻ, vì vậy phần nào kết thúc ở trang lẻ sẽ được
    chèn thêm một trang trắng.
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont("DemoNotice", str(font_path)))
    if not 1 <= len(paths) <= 2:
        raise ValueError("Cần một file hợp đồng, kèm hoặc không kèm thỏa thuận")
    contract_pdf = paths[0]
    trang_hop_dong, trang_phu_luc = tach_hop_dong_va_phu_luc(contract_pdf)

    phan = [
        ("Hợp đồng lao động", contract_pdf, trang_hop_dong),
        ("Phụ lục lương", contract_pdf, trang_phu_luc),
    ]
    # Vị trí không phải ký thỏa thuận thì bộ hồ sơ chỉ có hai phần.
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
