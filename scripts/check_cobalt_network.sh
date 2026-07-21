#!/usr/bin/env bash
set -euo pipefail

BOT_CONTAINER="${1:-}"
COBALT_CONTAINER="${2:-cobalt-api}"
NETWORK_NAME="${3:-cobalt-network}"

if [ -z "${BOT_CONTAINER}" ]; then
  BOT_CONTAINER="$(docker ps --format '{{.Names}}' | grep -E '(^bot-1$|cobalt-bot)' | head -1 || true)"
fi

if [ -z "${BOT_CONTAINER}" ]; then
  echo "ERROR: bot container not found. Pass it as first argument, e.g.:"
  echo "  $0 bot-1 cobalt-api"
  exit 1
fi

echo "Using bot container: ${BOT_CONTAINER}"

echo "=== Docker network check: ${NETWORK_NAME} ==="
if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
  echo "ERROR: network '${NETWORK_NAME}' does not exist"
  echo "Create it: docker network create ${NETWORK_NAME}"
  exit 1
fi

echo
echo "=== Bot container networks ==="
docker inspect "${BOT_CONTAINER}" --format '{{range $name, $cfg := .NetworkSettings.Networks}}{{$name}} {{end}}' 2>/dev/null || {
  echo "ERROR: bot container '${BOT_CONTAINER}' not found"
  exit 1
}

echo
echo "=== Cobalt container networks ==="
docker inspect "${COBALT_CONTAINER}" --format '{{range $name, $cfg := .NetworkSettings.Networks}}{{$name}} {{end}}' 2>/dev/null || {
  echo "ERROR: cobalt container '${COBALT_CONTAINER}' not found"
  echo "If Cobalt runs separately, connect it:"
  echo "  docker network connect ${NETWORK_NAME} <cobalt-container-name>"
  exit 1
}

echo
echo "=== DNS from bot: cobalt-api ==="
if docker exec "${BOT_CONTAINER}" getent hosts cobalt-api; then
  echo "OK: cobalt-api resolves inside bot container"
else
  echo "ERROR: cobalt-api does not resolve inside bot container"
  echo "Ensure Cobalt container is attached to ${NETWORK_NAME} with alias/name cobalt-api"
  exit 1
fi

echo
echo "=== Cobalt POST test from bot ==="
docker exec "${BOT_CONTAINER}" python -c "
import asyncio, aiohttp, os, json

async def main():
    url = os.getenv('COBALT_API_URL', 'http://cobalt-api:9000')
    payload = {
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'videoQuality': '480',
        'alwaysProxy': True,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers={'Accept': 'application/json'}) as resp:
            text = await resp.text()
            print(f'status={resp.status}')
            print(text[:500])

asyncio.run(main())
"

echo
echo "Done. If connection fails, run:"
echo "  docker network connect ${NETWORK_NAME} ${COBALT_CONTAINER}"
