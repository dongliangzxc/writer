#!/bin/bash
# Webnovel Write Workflow - Full Execution
# This script runs the complete chapter writing workflow

set -e

CHAPTER_NUM="$1"
CHAPTER_PADDED=$(printf "%04d" "$CHAPTER_NUM")

export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-/Users/dongliang04/Documents/个人/小说/女频/.claude}"
export PROJECT_ROOT="${PROJECT_ROOT:-/Users/dongliang04/Documents/个人/小说/女频/预知幻梦}"
export SCRIPTS_DIR="$CLAUDE_PLUGIN_ROOT/scripts"
export SKILL_ROOT="$CLAUDE_PLUGIN_ROOT/skills/webnovel-write"

echo "================================"
echo "Webnovel Write Workflow"
echo "Chapter: $CHAPTER_NUM"
echo "================================"
echo ""

# Check prerequisites
echo "[Preflight] Checking prerequisites..."
python -X utf8 "$SCRIPTS_DIR/webnovel.py" --project-root "$PROJECT_ROOT" preflight
echo "✓ Preflight passed"
echo ""

# Step 1: Context Agent
echo "[Step 1] Context Agent - Gathering context..."
python -X utf8 "$SCRIPTS_DIR/webnovel.py" \
    --project-root "$PROJECT_ROOT" \
    context -- --chapter "$CHAPTER_NUM" > "/tmp/ch${CHAPTER_NUM}_context.json"

if [ $? -ne 0 ]; then
    echo "✗ Context Agent failed"
    exit 1
fi
echo "✓ Context gathered"
echo ""

# Extract key info from context
echo "[Step 1.5] Extracting writing guidance..."
python -X utf8 "$SCRIPTS_DIR/webnovel.py" \
    --project-root "$PROJECT_ROOT" \
    extract-context --chapter "$CHAPTER_NUM" --format json > "/tmp/ch${CHAPTER_NUM}_guidance.json"
echo "✓ Writing guidance extracted"
echo ""

# Step 2A would be manual drafting by Claude
# Step 3-6 also need Claude's involvement

echo "================================"
echo "Workflow preparation complete!"
echo ""
echo "Next steps (manual by Claude):"
echo "1. Read context from: /tmp/ch${CHAPTER_NUM}_context.json"
echo "2. Draft chapter: $PROJECT_ROOT/正文/第${CHAPTER_PADDED}章.md"
echo "3. Run structural-checker for review"
echo "4. Polish the draft"
echo "5. Run data-agent to save metadata"
echo "6. Git commit"
echo "================================"
