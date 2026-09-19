#!/usr/bin/env bash
#
# Dựng ứng dụng lên Google Cloud Run.
#
# Cách dùng dễ nhất là chạy trong Google Cloud Shell (terminal có sẵn trong
# trình duyệt, đã cài sẵn gcloud, không phải cài gì lên máy Windows):
#
#   1. Mở https://console.cloud.google.com và chọn dự án của bạn
#   2. Bấm biểu tượng terminal ">_" ở góc trên bên phải
#   3. Chạy:
#        git clone https://github.com/Lehongkhanh782/E-Contract-PDF-HTVEDU.git
#        cd E-Contract-PDF-HTVEDU
#        git checkout claude/dazzling-fermat-qkjoee
#        bash deploy/cloudrun.sh
#
# Script hỏi những gì cần thiết, tự tạo tài khoản đăng nhập đầu tiên, cất
# mật khẩu vào Secret Manager rồi dựng dịch vụ. Chạy lại lần nữa để cập
# nhật phiên bản mới mà không mất tài khoản đã tạo.

set -euo pipefail

TEN_DICH_VU="${TEN_DICH_VU:-hop-dong}"
VUNG="${VUNG:-us-central1}"          # Chỉ 3 vùng có hạn mức miễn phí:
                                     # us-central1, us-east1, us-west1
BO_NHO="${BO_NHO:-1Gi}"              # 512Mi thường không đủ cho LibreOffice
THOI_GIAN_CHO="${THOI_GIAN_CHO:-120}"  # Tạo PDF mất 10-30 giây
SO_BAN_TOI_DA="${SO_BAN_TOI_DA:-3}"  # Chặn chi phí nếu bị gọi dồn dập

BI_MAT_KHOA="econtract-secret-key"
BI_MAT_TAI_KHOAN="econtract-users"

mau_xanh() { printf '\033[1;32m%s\033[0m\n' "$1"; }
mau_vang() { printf '\033[1;33m%s\033[0m\n' "$1"; }
loi() { printf '\033[1;31m%s\033[0m\n' "$1" >&2; exit 1; }

command -v gcloud >/dev/null || loi "Không tìm thấy lệnh gcloud. Hãy chạy script này trong Google Cloud Shell."
command -v python3 >/dev/null || loi "Không tìm thấy python3."

DU_AN="$(gcloud config get-value project 2>/dev/null || true)"
[ -n "$DU_AN" ] && [ "$DU_AN" != "(unset)" ] || loi "Chưa chọn dự án. Chạy: gcloud config set project TEN-DU-AN"

mau_xanh "Dự án: $DU_AN"
mau_xanh "Dịch vụ: $TEN_DICH_VU tại vùng $VUNG"
echo

# ---------- 1. Bật các dịch vụ cần dùng ----------
mau_xanh "[1/4] Bật các dịch vụ của Google Cloud (lần đầu mất vài phút)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

# ---------- 2. Khóa ký phiên đăng nhập ----------
mau_xanh "[2/4] Chuẩn bị khóa ký phiên đăng nhập..."
if gcloud secrets describe "$BI_MAT_KHOA" >/dev/null 2>&1; then
  echo "    Đã có sẵn, giữ nguyên để không làm mọi người bị đăng xuất."
else
  python3 -c "import secrets; print(secrets.token_urlsafe(48), end='')" \
    | gcloud secrets create "$BI_MAT_KHOA" --data-file=- --quiet
  echo "    Đã tạo mới."
fi

# ---------- 3. Danh sách tài khoản ----------
mau_xanh "[3/4] Chuẩn bị danh sách tài khoản đăng nhập..."
if gcloud secrets describe "$BI_MAT_TAI_KHOAN" >/dev/null 2>&1; then
  echo "    Đã có sẵn, giữ nguyên."
  echo "    Muốn thêm tài khoản thì xem phần cuối tài liệu docs/TRIEN_KHAI.md."
else
  echo
  mau_vang "    Chưa có tài khoản nào. Tạo tài khoản đăng nhập đầu tiên:"
  read -r -p "    Tên tài khoản (ví dụ nhansu): " TEN_TK
  [ -n "$TEN_TK" ] || loi "Tên tài khoản không được để trống."
  read -r -s -p "    Mật khẩu (ít nhất 10 ký tự, gõ không hiện): " MAT_KHAU; echo
  read -r -s -p "    Gõ lại mật khẩu: " MAT_KHAU_2; echo
  [ "$MAT_KHAU" = "$MAT_KHAU_2" ] || loi "Hai lần gõ không giống nhau."
  [ "${#MAT_KHAU}" -ge 10 ] || loi "Mật khẩu quá ngắn, cần ít nhất 10 ký tự."

  # Băm bằng đúng thuật toán mà ứng dụng dùng.
  TEN_TK="$TEN_TK" MAT_KHAU="$MAT_KHAU" python3 - <<'PY' | gcloud secrets create "$BI_MAT_TAI_KHOAN" --data-file=- --quiet
import json, os, sys
sys.path.insert(0, "backend")
from app.auth import hash_password

salt, digest = hash_password(os.environ["MAT_KHAU"])
print(json.dumps({"users": [{
    "username": os.environ["TEN_TK"].strip().lower(),
    "display_name": "Phòng Nhân sự",
    "salt": salt,
    "hash": digest,
    "units": ["*"],
}]}, ensure_ascii=False), end="")
PY
  unset MAT_KHAU MAT_KHAU_2
  echo "    Đã tạo tài khoản, phạm vi: tất cả 4 cơ sở."
fi

# Cho dịch vụ quyền đọc hai bí mật trên.
TAI_KHOAN_CHAY="$(gcloud projects describe "$DU_AN" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
for bi_mat in "$BI_MAT_KHOA" "$BI_MAT_TAI_KHOAN"; do
  gcloud secrets add-iam-policy-binding "$bi_mat" \
    --member="serviceAccount:$TAI_KHOAN_CHAY" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null
done

# ---------- 4. Dựng dịch vụ ----------
mau_xanh "[4/4] Build và dựng dịch vụ (lần đầu mất 5-10 phút)..."
echo

# --allow-unauthenticated để mở được web; việc chặn người lạ do màn hình
# đăng nhập của ứng dụng lo, không phải do Google.
gcloud run deploy "$TEN_DICH_VU" \
  --source . \
  --region "$VUNG" \
  --platform managed \
  --allow-unauthenticated \
  --memory "$BO_NHO" \
  --cpu 1 \
  --timeout "$THOI_GIAN_CHO" \
  --max-instances "$SO_BAN_TOI_DA" \
  --set-secrets "ECONTRACT_SECRET_KEY=${BI_MAT_KHOA}:latest,ECONTRACT_USERS=${BI_MAT_TAI_KHOAN}:latest" \
  --quiet

DIA_CHI="$(gcloud run services describe "$TEN_DICH_VU" --region "$VUNG" --format='value(status.url)')"

echo
mau_xanh "================================================================"
mau_xanh " Xong. Mở địa chỉ sau, phải thấy màn hình đăng nhập:"
mau_xanh " $DIA_CHI"
mau_xanh "================================================================"
echo
echo "Việc tiếp theo:"
echo "  1. Đăng nhập và bấm 'Điền hồ sơ mẫu để thử', rồi 'Tạo và tải PDF'"
echo "  2. Gắn tên miền riêng:"
echo "       gcloud beta run domain-mappings create \\"
echo "         --service $TEN_DICH_VU --region $VUNG --domain hopdong.tenmiencuaban.vn"
echo "     Sau đó thêm các bản ghi DNS mà lệnh trên in ra."
echo "  3. Đặt cảnh báo ngân sách ở mục Billing để yên tâm."
