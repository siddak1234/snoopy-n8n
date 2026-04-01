FROM n8nio/n8n:2.8.3@sha256:53004142b0e93de1e9e31943e601ed9bd4b24ca82a307864ccadf1820b627e5e

# Install external packages used by Code node allowlist
USER root
RUN npm install -g --omit=dev pdf-lib@1.17.1
RUN ln -sf "$(npm root -g)/pdf-lib" /usr/local/lib/node_modules/n8n/node_modules/pdf-lib
USER node
