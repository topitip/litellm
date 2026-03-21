#!/bin/sh
set -e

# Start gost as HTTP→SOCKS5 bridge if SOCKS5_PROXY is set
if [ -n "$SOCKS5_PROXY" ]; then
    echo "[entrypoint] Starting gost HTTP→SOCKS5 bridge: $SOCKS5_PROXY"
    gost -L "http://127.0.0.1:${GOST_PORT:-8080}" -F "$SOCKS5_PROXY" &
    GOST_PID=$!
    sleep 1

    if kill -0 $GOST_PID 2>/dev/null; then
        echo "[entrypoint] gost running on :${GOST_PORT:-8080}"
        export HTTPS_PROXY="http://127.0.0.1:${GOST_PORT:-8080}"
        export HTTP_PROXY="http://127.0.0.1:${GOST_PORT:-8080}"
        export AIOHTTP_TRUST_ENV=true
        # Exclude internal traffic from proxy
        export NO_PROXY="localhost,127.0.0.1"
    else
        echo "[entrypoint] WARNING: gost failed to start, proceeding without proxy"
    fi
fi

exec litellm "$@"
