#!/bin/bash
# webnovel-write workflow executor
# Usage: execute.sh <chapter_num>

set -e

CHAPTER="$1"
if [ -z "$CHAPTER" ]; then
    echo "Error: Chapter number required"
    exit 1
fi

export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-/Users/dongliang04/Documents/个人/小说/女频/.claude}"
export PROJECT_ROOT="${PROJECT_ROOT:-/Users/dongliang04/Documents/个人/小说/女频/预知幻梦}"
export SCRIPTS_DIR="$CLAUDE_PLUGIN_ROOT/scripts"

echo "=== Webnovel Write Workflow ==="
echo "Chapter: $CHAPTER"
echo "Project: $PROJECT_ROOT"
echo ""

# Step 1: Context Agent
echo "[Step 1] Running Context Agent..."
python -X utf8 "$SCRIPTS_DIR/webnovel.py" \
    --project-root "$PROJECT_ROOT" \
    context -- --chapter "$CHAPTER" > "/tmp/ch${CHAPTER}_context.json"

if [ $? -ne 0 ]; then
    echo "Error: Context Agent failed"
    exit 1
fi

echo "Context built successfully"
echo ""

# Note: Steps 2-6 would be executed by Claude Code reading the agent prompts
# This script just prepares the context

echo "=== Workflow prepared ==="
echo "Context saved to: /tmp/ch${CHAPTER}_context.json"
echo "Ready for Step 2A: Drafting"
