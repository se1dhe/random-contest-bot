#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

BASE_URL="${BASE_URL:-http://localhost:8000}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

pass() {
  echo "✅ $1"
}

fail() {
  echo "❌ $1"
  exit 1
}

request() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local out_file="$4"
  local code

  if [ -n "$body" ]; then
    code="$(curl -sS -o "$out_file" -w "%{http_code}" -X "$method" \
      -H "Content-Type: application/json" \
      "$url" \
      --data "$body")"
  else
    code="$(curl -sS -o "$out_file" -w "%{http_code}" -X "$method" "$url")"
  fi

  echo "$code"
}

echo "[1/10] Web root check"
ROOT_CODE="$(request GET "$BASE_URL/" "" "$TMP_DIR/root.json")"
[ "$ROOT_CODE" = "200" ] || fail "GET / expected 200, got $ROOT_CODE"
pass "GET / -> 200"

echo "[2/10] Public contest not found check"
NOT_FOUND_CODE="$(request GET "$BASE_URL/api/contests/999999999" "" "$TMP_DIR/contest_404.json")"
[ "$NOT_FOUND_CODE" = "404" ] || fail "GET /api/contests/999999999 expected 404, got $NOT_FOUND_CODE"
pass "Public contest endpoint returns 404 for unknown contest"

echo "[3/10] Admin unauthorized guard"
ADMIN_FORBIDDEN_CODE="$(request GET "$BASE_URL/api/admin/contests" "" "$TMP_DIR/admin_forbidden.json")"
[ "$ADMIN_FORBIDDEN_CODE" = "403" ] || fail "GET /api/admin/contests without auth expected 403, got $ADMIN_FORBIDDEN_CODE"
pass "Admin endpoint is protected"

echo "[4/10] Publish unauthorized guard"
PUBLISH_FORBIDDEN_CODE="$(request POST "$BASE_URL/api/publish/contest/1" "" "$TMP_DIR/publish_forbidden.json")"
[ "$PUBLISH_FORBIDDEN_CODE" = "403" ] || fail "POST /api/publish/contest/1 without auth expected 403, got $PUBLISH_FORBIDDEN_CODE"
pass "Publish endpoint is protected"

echo "[5/10] OAuth provider status endpoints"
for provider in instagram tiktok; do
  STATUS_CODE="$(request GET "$BASE_URL/api/$provider/status" "" "$TMP_DIR/${provider}_status.json")"
  [ "$STATUS_CODE" = "200" ] || fail "GET /api/$provider/status expected 200, got $STATUS_CODE"
  python3 - "$TMP_DIR/${provider}_status.json" "$provider" <<'PY'
import json, sys
path, provider = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
for key in ("configured", "enabled", "redirect_uri"):
    if key not in data:
        raise SystemExit(f"{provider} status missing key: {key}")
if not isinstance(data["redirect_uri"], str) or not data["redirect_uri"]:
    raise SystemExit(f"{provider} redirect_uri is empty")
print("OK")
PY
done
pass "OAuth status endpoints return valid schema"

echo "[6/10] Admin validation check (invalid status)"
INVALID_STATUS_CODE="$(request GET "$BASE_URL/api/admin/contests?status=unknown&user_id=0" "" "$TMP_DIR/admin_invalid_status.json")"
if [ "$INVALID_STATUS_CODE" != "403" ] && [ "$INVALID_STATUS_CODE" != "400" ]; then
  fail "Expected 403 or 400 for invalid status check, got $INVALID_STATUS_CODE"
fi
pass "Invalid admin request does not return 500"

echo "[7/10] Optional public contest auto-check"
if [ -n "${TEST_PUBLIC_CONTEST_ID:-}" ] && [ -n "${TEST_PUBLIC_USER_ID:-}" ]; then
  AUTO_CHECK_CODE="$(request GET "$BASE_URL/api/contests/$TEST_PUBLIC_CONTEST_ID/auto-check?user_id=$TEST_PUBLIC_USER_ID" "" "$TMP_DIR/auto_check.json")"
  [ "$AUTO_CHECK_CODE" = "200" ] || fail "GET /api/contests/$TEST_PUBLIC_CONTEST_ID/auto-check expected 200, got $AUTO_CHECK_CODE"
  python3 - "$TMP_DIR/auto_check.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
for key in ("is_registered", "can_register", "status", "conditions", "participants_count"):
    if key not in data:
        raise SystemExit(f"auto-check missing key: {key}")
if not isinstance(data["conditions"], list):
    raise SystemExit("auto-check conditions is not a list")
print("OK")
PY
  pass "Public auto-check endpoint returns valid schema"
else
  echo "ℹ️  TEST_PUBLIC_CONTEST_ID or TEST_PUBLIC_USER_ID not set, skipping public auto-check"
fi

echo "[8/10] Optional authorized checks"
if [ -n "${ADMIN_AUTH:-}" ]; then
  AUTHED_CONTESTS_CODE="$(curl -sS -o "$TMP_DIR/admin_contests_paged.json" -w "%{http_code}" \
    "$BASE_URL/api/admin/contests?paginated=true&limit=5&offset=0&_auth=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$ADMIN_AUTH")")"
  [ "$AUTHED_CONTESTS_CODE" = "200" ] || fail "Authorized paginated contests expected 200, got $AUTHED_CONTESTS_CODE"
  python3 - "$TMP_DIR/admin_contests_paged.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
if not isinstance(data, dict):
    raise SystemExit("Paginated response is not an object")
for key in ("items", "total", "limit", "offset"):
    if key not in data:
        raise SystemExit(f"Missing key in paginated response: {key}")
if not isinstance(data["items"], list):
    raise SystemExit("items is not a list")
print("OK")
PY
  pass "Authorized paginated contests schema is valid"

  GROWTH_CODE="$(curl -sS -o "$TMP_DIR/admin_growth.json" -w "%{http_code}" \
    "$BASE_URL/api/admin/analytics/growth?days=7&_auth=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$ADMIN_AUTH")")"
  [ "$GROWTH_CODE" = "200" ] || fail "Authorized growth analytics expected 200, got $GROWTH_CODE"
  python3 - "$TMP_DIR/admin_growth.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
if not isinstance(data, list):
    raise SystemExit("growth response is not a list")
for item in data:
    if "date" not in item or "participants" not in item:
        raise SystemExit("growth response item missing keys")
print("OK")
PY
  pass "Growth analytics endpoint returns valid schema"

  if [ -n "${TEST_CONTEST_ID:-}" ]; then
    DIFF_CODE="$(curl -sS -o "$TMP_DIR/republish_diff.json" -w "%{http_code}" \
      "$BASE_URL/api/admin/contests/$TEST_CONTEST_ID/republish-diff?_auth=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$ADMIN_AUTH")")"
    if [ "$DIFF_CODE" != "200" ] && [ "$DIFF_CODE" != "404" ] && [ "$DIFF_CODE" != "400" ]; then
      fail "Republish diff check expected 200/400/404, got $DIFF_CODE"
    fi
    pass "Republish diff endpoint responds with expected status set"
  else
    echo "ℹ️  TEST_CONTEST_ID not set, skipping diff endpoint check"
  fi
else
  echo "ℹ️  ADMIN_AUTH not set, skipping authorized regression checks"
fi

echo "[9/10] Instagram auth endpoint smoke"
INSTAGRAM_AUTH_CODE="$(request GET "$BASE_URL/api/instagram/auth?contest_id=1&user_id=1" "" "$TMP_DIR/instagram_auth_redirect.html")"
if [ "$INSTAGRAM_AUTH_CODE" != "302" ] && [ "$INSTAGRAM_AUTH_CODE" != "307" ] && [ "$INSTAGRAM_AUTH_CODE" != "500" ]; then
  fail "Instagram auth endpoint expected redirect or configuration error status, got $INSTAGRAM_AUTH_CODE"
fi
pass "Instagram auth endpoint responds without route errors"

echo "[10/10] Completed"
echo "API regression checks passed"
