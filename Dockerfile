# Onkyo AVR for Remote Two/3 + Roon - container image (e.g. for Proxmox)
#
#   docker build -t onkyo-remotetwo .
#   docker run -d --network host -v ./data:/data \
#     -e ONKYO_HOST=192.168.0.54 -e ROON_SOURCE="BD/DVD" onkyo-remotetwo
#
# Host networking is required: Roon discovery (UDP multicast) and, in
# MODE=full, mDNS so the Remote finds the integration.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODE=roon \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --system --uid 1000 --home /app onkyo \
 && mkdir -p /data && chown onkyo /data

COPY driver.json ./
COPY assets/onkyo.png ./
COPY intg-onkyoavr/ ./intg-onkyoavr/

USER onkyo
VOLUME /data

CMD ["python", "intg-onkyoavr/container.py"]
