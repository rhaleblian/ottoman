#!/usr/bin/env bash
set -euo pipefail

USER_ID="${USER_ID:-1000}"
GROUP_ID="${GROUP_ID:-1000}"

echo "[daemon] starting ottoman..."

if [ "$(id -u)" = "0" ]; then
    getent group "${GROUP_ID}" >/dev/null 2>&1 || groupadd --gid "${GROUP_ID}" appgroup
    id -u "${USER_ID}" >/dev/null 2>&1 || useradd --uid "${USER_ID}" --gid "${GROUP_ID}" --create-home appuser

    for dir in /app/daemon /app/input /app/models /app/workflows; do
        if [ -e "${dir}" ]; then
            find "${dir}" \( ! -user "${USER_ID}" -o ! -group "${GROUP_ID}" \) \
                -exec chown -h "${USER_ID}:${GROUP_ID}" {} +
        fi
    done

    echo "[daemon] running as ${USER_ID}:${GROUP_ID}"
    exec gosu "${USER_ID}:${GROUP_ID}" python -m daemon.daemon
fi

exec python -m daemon.daemon
