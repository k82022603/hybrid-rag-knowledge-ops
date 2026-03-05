#!/bin/bash
# ==============================================================================
# RAGAS Weekly Evaluation Wrapper Script
# ==============================================================================
#
# Purpose: Execute RAGAS v10 evaluation inside kp-ai-service container,
#          extract results, and judge quality gate pass/fail.
#
# Usage:
#   ./scripts/ragas_weekly_eval.sh
#
# Exit codes:
#   0 = PASS (all metrics above thresholds)
#   1 = FAIL (one or more metrics below thresholds)
#   2 = ERROR (execution failure, missing container, etc.)
#
# Quality Thresholds:
#   Faithfulness    > 0.85
#   Answer Relevancy > 0.60
#   Mean            > 0.65
#
# Output:
#   /tmp/ragas_weekly_YYYYMMDD.json
#
# Updated: 2026-03-05
# ==============================================================================

set -euo pipefail

# --- Configuration ---
CONTAINER_NAME="kp-ai-service"
RAGAS_SCRIPT="/app/scripts/ragas_v10_post_entity_eval.py"
CONTAINER_RESULT="/tmp/ragas_v10_post_entity_result.json"

EVAL_DATE=$(date +%Y%m%d)
HOST_RESULT="/tmp/ragas_weekly_${EVAL_DATE}.json"

# Quality Thresholds
FAITH_THRESHOLD=0.85
RELEV_THRESHOLD=0.60
MEAN_THRESHOLD=0.65

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Functions ---
log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Pre-flight Checks ---
log_info "RAGAS Weekly Evaluation - $EVAL_DATE"
echo "=============================================="

# Check container is running
if ! docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "running"; then
    log_error "Container '$CONTAINER_NAME' is not running."
    log_error "Start it with: docker-compose up -d ai-service"
    exit 2
fi

# Check dependent containers
DEPS=("kp-elasticsearch" "kp-neo4j" "kp-postgresql")
for dep in "${DEPS[@]}"; do
    if ! docker inspect -f '{{.State.Status}}' "$dep" 2>/dev/null | grep -q "running"; then
        log_warn "Dependency container '$dep' is not running."
    fi
done

# --- Execute RAGAS Evaluation ---
log_info "Running RAGAS v10 evaluation inside container..."
log_info "Script: $RAGAS_SCRIPT"
echo ""

EVAL_START=$(date +%s)

docker exec "$CONTAINER_NAME" \
    python3 "$RAGAS_SCRIPT" 2>&1 | tee "/tmp/ragas_eval_${EVAL_DATE}.log"

EVAL_EXIT=${PIPESTATUS[0]}
EVAL_END=$(date +%s)
EVAL_DURATION=$((EVAL_END - EVAL_START))

log_info "Evaluation completed in ${EVAL_DURATION}s (exit code: $EVAL_EXIT)"

if [ $EVAL_EXIT -ne 0 ]; then
    log_error "RAGAS evaluation script failed with exit code $EVAL_EXIT"
    exit 2
fi

# --- Extract Result File ---
log_info "Extracting result file from container..."

docker cp "${CONTAINER_NAME}:${CONTAINER_RESULT}" "$HOST_RESULT" 2>/dev/null

if [ ! -f "$HOST_RESULT" ]; then
    log_error "Result file not found at $HOST_RESULT"
    log_error "Check container logs: docker logs $CONTAINER_NAME"
    exit 2
fi

log_info "Result saved: $HOST_RESULT"

# --- Quality Gate Judgment ---
echo ""
echo "=============================================="
log_info "Quality Gate Assessment"
echo "=============================================="

# Extract metrics using python3
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    log_error "Python not found. Cannot parse results."
    exit 2
fi

GATE_RESULT=$($PYTHON_CMD << 'PYEOF'
import json
import sys

result_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ragas_weekly_result.json"

try:
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"ERROR: Failed to parse result JSON: {e}", file=sys.stderr)
    sys.exit(2)

metrics = data.get("metrics", {})
faithfulness = metrics.get("faithfulness", 0.0)
answer_relevancy = metrics.get("answer_relevancy", 0.0)
context_precision = metrics.get("context_precision", 0.0)
context_recall = metrics.get("context_recall", 0.0)
mean = (faithfulness + answer_relevancy) / 2

# Thresholds
FAITH_T = 0.85
RELEV_T = 0.60
MEAN_T = 0.65

faith_pass = faithfulness >= FAITH_T
relev_pass = answer_relevancy >= RELEV_T
mean_pass = mean >= MEAN_T

print(f"  Faithfulness:      {faithfulness:.4f}  (threshold: {FAITH_T})  {'PASS' if faith_pass else 'FAIL'}")
print(f"  Answer Relevancy:  {answer_relevancy:.4f}  (threshold: {RELEV_T})  {'PASS' if relev_pass else 'FAIL'}")
print(f"  Context Precision: {context_precision:.4f}")
print(f"  Context Recall:    {context_recall:.4f}")
print(f"  Mean (F+R/2):      {mean:.4f}  (threshold: {MEAN_T})  {'PASS' if mean_pass else 'FAIL'}")
print()

# Quality gate distribution
qg = data.get("quality_gate", {})
if qg:
    print(f"  Quality Gate: HIGH={qg.get('HIGH',0)}, PARTIAL={qg.get('PARTIAL',0)}, NONE={qg.get('NONE',0)}")

all_pass = faith_pass and relev_pass and mean_pass
if all_pass:
    print()
    print("  VERDICT: PASS")
    sys.exit(0)
else:
    print()
    print("  VERDICT: FAIL")
    sys.exit(1)
PYEOF
)
GATE_EXIT=$?

echo "$GATE_RESULT"

# --- Final Output ---
echo ""
echo "=============================================="
if [ $GATE_EXIT -eq 0 ]; then
    log_info "Quality Gate: PASS"
    log_info "Result file: $HOST_RESULT"
    exit 0
elif [ $GATE_EXIT -eq 1 ]; then
    log_warn "Quality Gate: FAIL"
    log_warn "Result file: $HOST_RESULT"
    log_warn "Investigate metrics and review search quality."
    exit 1
else
    log_error "Quality Gate: ERROR (could not parse results)"
    exit 2
fi
