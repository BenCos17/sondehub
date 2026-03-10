# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM=ghcr.io/hassio-addons/base:18.1.1
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    python3-dev \
    py3-pip \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy main script
COPY rootfs/usr/bin/sondehub_addon.py /app/sondehub_addon.py

# Copy s6 service files
COPY rootfs/ /

# Set permissions for s6 services
RUN chmod a+x /etc/services.d/sondehub/run && \
    chmod a+x /etc/services.d/sondehub/finish

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD pgrep -f "sondehub_addon.py" >/dev/null || exit 1
