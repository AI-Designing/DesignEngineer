#!/usr/bin/env bash
# Visible demo for LinkedIn screenshots: API server logs + browser at /docs
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=============================================="
echo " AI Designer — Screenshot Demo"
echo "=============================================="
echo ""

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  echo "[OK] Loaded .env"
else
  echo "[WARN] No .env — set OPPER_API_KEY and FREECAD_PATH"
fi

# Optional FreeCAD path for headless execution (set in .env or export manually)
if [ -n "${FREECAD_PATH:-}" ] && [ -x "$FREECAD_PATH" ]; then
  echo "[OK] FREECAD_PATH=$FREECAD_PATH"
elif command -v freecadcmd >/dev/null 2>&1; then
  export FREECAD_PATH="$(command -v freecadcmd)"
  echo "[OK] FREECAD_PATH=$FREECAD_PATH (from PATH)"
fi

echo ""
echo "Step 1 — Open in your browser (for side-by-side screenshot):"
echo "  → http://127.0.0.1:8000/docs"
echo ""
echo "Step 2 — If API is not running, open a SECOND terminal and run:"
echo "  cd $(pwd)"
echo "  source .env && PYTHONUNBUFFERED=1 python3 -m uvicorn ai_designer.api.app:app --host 127.0.0.1 --port 8000"
echo ""

echo "Step 3 — Health check:"
curl -s http://127.0.0.1:8000/health | python3 -m json.tool || {
  echo "[ERROR] API not reachable on :8000. Start uvicorn first (see Step 2)."
  exit 1
}

echo ""
echo "Step 4 — Submit design (primitive cube — works with current generator):"
RESP=$(curl -s -X POST http://127.0.0.1:8000/api/v1/design \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Create a 10x10x10 mm cube using ONLY create_box. No PartDesign, no sketches.","max_iterations":3}')
echo "$RESP" | python3 -m json.tool
REQ=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['request_id'])")
echo ""
echo "Request ID: $REQ"
echo "Polling status (watch API terminal for agent logs)..."
echo ""

for i in $(seq 1 30); do
  sleep 5
  BODY=$(curl -s "http://127.0.0.1:8000/api/v1/design/$REQ")
  STATUS=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
  SCORE=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('validation_score','-'))")
  echo "[$i] status=$STATUS  validation_score=$SCORE"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo ""
    echo "Final response:"
    echo "$BODY" | python3 -m json.tool
    break
  fi
done

echo ""
echo "Outputs (if execution succeeded): ls -la outputs/"
ls -la outputs/ 2>/dev/null | tail -5 || true
