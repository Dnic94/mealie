#!/usr/bin/env bash
set -euo pipefail

FEATURE_BRANCH="TagGroups"
UPSTREAM_BRANCH="upstream/mealie-next"
COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"

cd "$(dirname "$0")"

echo "==> Fetching upstream..."
git fetch upstream

echo "==> Checking out $FEATURE_BRANCH..."
git checkout "$FEATURE_BRANCH"

echo "==> Rebasing onto $UPSTREAM_BRANCH..."
if ! git rebase "$UPSTREAM_BRANCH"; then
    echo ""
    echo "ERROR: Rebase conflict detected."
    echo "Resolve conflicts manually, then run:"
    echo "  git rebase --continue"
    echo "  docker compose build"
    echo "  docker compose up -d"
    git rebase --abort 2>/dev/null || true
    exit 1
fi

echo "==> Building Docker image (this takes ~10-15 minutes)..."
docker compose -f "$COMPOSE_FILE" build

echo "==> Restarting container..."
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Done! Mealie is running with your custom TagGroups patch."
echo "To push the rebased branch to your fork:"
echo "  git push origin $FEATURE_BRANCH --force-with-lease"
