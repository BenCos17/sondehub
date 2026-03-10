# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Install sondehub SDK and pin paho-mqtt to v1.x (sondehub 0.3.x requires the v1 API)
RUN pip3 install --no-cache-dir \
    "sondehub==0.3.2" \
    "paho-mqtt<2.0"

# Copy root filesystem
COPY rootfs /
