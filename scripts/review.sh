#!/usr/bin/env bash
#
# Trigger an AI review of a pull request from the terminal and print the result —
# no clicking through the UI. Requires the API + a Celery worker running, and Ollama
# up (see startcmd.md).
#
# Auth: set REVIEWIQ_TOKEN to your JWT. After signing in via the SPA, copy the
# `reviewiq_token` cookie value (browser DevTools → Application → Cookies).
#
# Usage:
#   REVIEWIQ_TOKEN=<jwt> ./scripts/review.sh <repository_id> <pull_number>
#   REVIEWIQ_TOKEN=<jwt> API=http://localhost:8000 ./scripts/review.sh <repo_id> 42
#
set -euo pipefail

API="${API:-http://localhost:8000}"
TOKEN="${REVIEWIQ_TOKEN:?Set REVIEWIQ_TOKEN to your JWT (the reviewiq_token cookie after signing in)}"
REPO="${1:?Usage: review.sh <repository_id> <pull_number>}"
PR="${2:?Usage: review.sh <repository_id> <pull_number>}"
AUTH="Authorization: Bearer ${TOKEN}"

jqget() { python3 -c "import sys,json; print(json.load(sys.stdin)${1})"; }

echo "→ Triggering review of PR #${PR} ..."
resp=$(curl -fsS -X POST "${API}/api/v1/reviews" \
  -H "${AUTH}" -H "Content-Type: application/json" \
  -d "{\"repository_id\":\"${REPO}\",\"pull_number\":${PR}}")
review_id=$(printf '%s' "${resp}" | jqget "['review_id']")
job_id=$(printf '%s' "${resp}" | jqget "['job_id']")
echo "  review_id=${review_id}  job_id=${job_id}"

echo "→ Waiting for the job to finish ..."
while true; do
  status=$(curl -fsS "${API}/api/v1/jobs/${job_id}" -H "${AUTH}" | jqget "['status']")
  echo "  job: ${status}"
  case "${status}" in
    succeeded) break ;;
    failed) echo "Review job failed (is Ollama running? is the repo indexed?)."; exit 1 ;;
  esac
  sleep 2
done

echo "→ Review result:"
curl -fsS "${API}/api/v1/reviews/${review_id}" -H "${AUTH}" | python3 -m json.tool
