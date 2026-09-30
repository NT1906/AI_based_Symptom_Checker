#!/usr/bin/env bash
# @file Zero-surprise deploy on the VPS: pull an image, restart, wait for health, roll back on failure.
# Called by .github/workflows/cd.yml over SSH; can also be run by hand.
# Usage: ./deploy.sh ghcr.io/<owner>/symptom-checker-api:<git-sha>
set -euo pipefail
cd "$(dirname "$0")"

IMAGE="${1:?usage: deploy.sh <image-ref>}"
COMPOSE="docker compose -f docker-compose.prod.yml"
STATE=.deploy-state          # remembers the last healthy image for rollback
HEALTH_TRIES=36              # 36 x 5 s = 3 minutes

previous="$(cat "$STATE" 2>/dev/null || true)"

wait_healthy() {
  for _ in $(seq 1 "$HEALTH_TRIES"); do
    status="$(docker inspect -f '{{.State.Health.Status}}' symptom-checker-api 2>/dev/null || echo starting)"
    [ "$status" = "healthy" ] && return 0
    sleep 5
  done
  return 1
}

echo "Deploying $IMAGE (previous: ${previous:-none})"
API_IMAGE="$IMAGE" $COMPOSE pull api
API_IMAGE="$IMAGE" $COMPOSE up -d --remove-orphans

if wait_healthy; then
  echo "$IMAGE" > "$STATE"
  docker image prune -f > /dev/null
  echo "Deploy OK: $IMAGE"
else
  echo "New version is unhealthy. Last logs:"; docker logs --tail 50 symptom-checker-api || true
  if [ -n "$previous" ]; then
    echo "Rolling back to $previous"
    API_IMAGE="$previous" $COMPOSE up -d --remove-orphans
    wait_healthy && echo "Rollback OK" || echo "Rollback is unhealthy too. Manual attention needed."
  fi
  exit 1
fi
