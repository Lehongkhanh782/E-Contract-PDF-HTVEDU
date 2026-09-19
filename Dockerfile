# Đóng gói ứng dụng thành một image chạy được ở mọi nơi.
#
# Gồm hai chặng: chặng đầu build giao diện bằng Node, chặng sau chỉ giữ
# Python và LibreOffice nên image không mang theo node_modules.

# ---------- Chặng 1: build giao diện ----------
FROM node:22-slim AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Chặng 2: máy chủ ----------
FROM python:3.11-slim

# libreoffice-writer là bắt buộc: thiếu nó thì không mở được file Word và
# chương trình báo "Không chuyển được Word sang PDF".
# fonts-dejavu-core cung cấp font cho dòng đánh dấu bản thử nghiệm.
# fonts-liberation thay cho các font Microsoft để giữ bố cục mẫu Word.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libreoffice-writer \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY contract_kit/ contract_kit/
COPY --from=frontend /build/dist frontend/dist

# Chạy bằng tài khoản thường, không phải root.
# LibreOffice cần một thư mục nhà có quyền ghi để tạo hồ sơ tạm.
RUN useradd --create-home --uid 10001 econtract \
    && chown -R econtract:econtract /app
USER econtract
ENV HOME=/home/econtract

EXPOSE 8000

# Nền tảng lưu trữ tự đặt biến PORT; mặc định 8000 khi chạy ở máy cá nhân.
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --app-dir backend"]
