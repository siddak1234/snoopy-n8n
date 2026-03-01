FROM alpine:3.22 AS pdf-tools

RUN apk add --no-cache --root /opt/pdf-rootfs --initdb \
    --repositories-file /etc/apk/repositories \
    --keys-dir /etc/apk/keys \
    poppler-utils \
    ghostscript \
    qpdf \
    mupdf-tools \
    bash \
    fontconfig \
    ttf-dejavu

FROM n8nio/n8n:latest

USER root

COPY --from=pdf-tools /opt/pdf-rootfs/ /

USER node
