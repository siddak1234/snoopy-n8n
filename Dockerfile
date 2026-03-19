FROM n8nio/n8n:latest

# Install external packages used by Code node allowlist
USER root
RUN npm install -g --omit=dev pdf-lib
RUN ln -sf "$(npm root -g)/pdf-lib" /usr/local/lib/node_modules/n8n/node_modules/pdf-lib
USER node
