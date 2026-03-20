FROM n8nio/n8n:2.8.3
# TODO: Pin base image by digest after CI validation, e.g.:
# FROM n8nio/n8n:2.8.3@sha256:<validated_digest>

# Install external packages used by Code node allowlist
USER root
RUN npm install -g --omit=dev pdf-lib@1.17.1
RUN ln -sf "$(npm root -g)/pdf-lib" /usr/local/lib/node_modules/n8n/node_modules/pdf-lib
USER node
