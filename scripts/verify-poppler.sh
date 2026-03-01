#!/bin/sh
set -eu

docker exec snoopy-n8n sh -lc '
command -v pdftoppm
pdftoppm -h | head -n 3
'
