"""PreToolUse hook: stop shell commands that touch attack payloads or raw transcripts.

These folders hold prompt-injection text. Claude should read only
sandbox/results/summary.json (numbers and ids).
"""
import json
import re
import sys

PROTECTED = re.compile(r"benchmark[/\\]+payloads|results[/\\]+raw", re.IGNORECASE)

data = json.load(sys.stdin)
cmd = str(data.get("tool_input", {}).get("command", ""))
if PROTECTED.search(cmd):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Blocked: command references sandbox/benchmark/payloads or "
            "sandbox/results/raw (prompt-injection data). Read sandbox/results/summary.json instead."}}))
sys.exit(0)
