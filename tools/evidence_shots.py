"""Evidence screenshots for the final slides: real command output, drawn as a terminal window with the key
lines boxed (consultation 30 Oct: "highlight key lines of evidence"; "show that we host it in a container").

    python tools/evidence_shots.py                  (from the repo root; Docker running)
    python tools/evidence_shots.py demo camel       (only these shots; demo and --live need Ollama)

Every image is the captured stdout of the command printed on its first line, run when the script runs;
nothing is typed in by hand. The demo runs without --show-email, so no attack text is shown.
Writes 2_Presentation_Prep/evidence/<shot>.png (git-ignored, like the deck).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import textwrap
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "sandbox"
OUT = ROOT / "2_Presentation_Prep" / "evidence"
FONT = "C:/Windows/Fonts/CascadiaMono.ttf"
SCALE, SIZE, PAD, LINE = 2, 15, 18, 1.45
MAX_CH = 124  # longer lines are cut with an ellipsis; labels go in a gutter to the right
BG, BAR, FG, DIM = "#0C0C0C", "#2B2B2B", "#D4D4D4", "#8A8A8A"
GREEN, RED, YELLOW, BLUE = "#4EC96B", "#F05454", "#F2C94C", "#5AA9F5"
PROMPT = r"PS ...\sandbox> "


def run(cmd: list[str], env: dict | None = None) -> list[str]:
    out = subprocess.run(cmd, cwd=SANDBOX, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env={**os.environ, "NO_COLOR": "1", **(env or {})})
    lines = [l.rstrip() for l in out.stdout.splitlines()]
    return [l for l in lines if not re.search(r"orphan containers|^\s*Container sandbox", l)]


def colour(line: str) -> str:
    if line.startswith(PROMPT):
        return YELLOW
    if re.search(r"ALLOWED|HIJACKED|FAIL", line):
        return RED
    if re.search(r"\bPASS\b|BLOCKED|SAFE|: done|isolation OK|=true|Internal=true", line):
        return GREEN
    return FG


def render(name: str, title: str, lines: list[str], boxes: list[tuple[str, str, str]], caption: str, size: int = SIZE):
    """boxes: (regex, colour, label). Every line matching a regex gets a box; the label is drawn once."""
    f = ImageFont.truetype(FONT, size * SCALE)
    width_ch = min(MAX_CH, max(len(l) for l in lines))
    lines = [l if len(l) <= width_ch else l[:width_ch - 1] + "…" for l in lines]
    ch_w = f.getbbox("M")[2]
    lh = int(size * SCALE * LINE)
    bar = 34 * SCALE
    gutter = max([len(lab) for _, _, lab in boxes if lab] + [0])
    gutter = (gutter + 4) * ch_w if gutter else 0
    w = PAD * SCALE * 2 + ch_w * width_ch + gutter
    h = bar + PAD * SCALE * 2 + lh * len(lines) + lh * 2
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, bar], fill=BAR)
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        cx = (16 + 22 * i) * SCALE
        d.ellipse([cx - 6 * SCALE, bar / 2 - 6 * SCALE, cx + 6 * SCALE, bar / 2 + 6 * SCALE], fill=c)
    d.text((90 * SCALE, bar / 2), title, font=f, fill=DIM, anchor="lm")
    y0 = bar + PAD * SCALE
    labelled = set()
    for i, line in enumerate(lines):
        y = y0 + i * lh
        for pat, col, label in boxes:
            if re.search(pat, line):
                x1 = PAD * SCALE - 6 * SCALE
                x2 = PAD * SCALE + ch_w * min(width_ch, max(len(line), 20)) + 6 * SCALE
                d.rounded_rectangle([x1, y - 3 * SCALE, x2, y + lh - 2 * SCALE], radius=5 * SCALE,
                                    outline=col, width=3 * SCALE)
                if label and pat not in labelled:
                    labelled.add(pat)
                    tw = f.getlength(label)
                    d.rounded_rectangle([w - PAD * SCALE - tw - 16 * SCALE, y - 3 * SCALE, w - PAD * SCALE,
                                         y + lh - 2 * SCALE], radius=5 * SCALE, fill=col)
                    d.text((w - PAD * SCALE - 8 * SCALE, y + lh / 2 - 2 * SCALE), label, font=f, fill="#111111",
                           anchor="rm")
                break
        d.text((PAD * SCALE, y), line, font=f, fill=colour(line))
    d.text((PAD * SCALE, y0 + lh * (len(lines) + 0.6)), caption, font=f, fill=DIM)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{name}.png")
    (OUT / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")  # read by build_deck.py
    print(f"wrote {(OUT / f'{name}.png').relative_to(ROOT)} ({len(lines)} lines)")


def stamp() -> str:
    return f"Captured {date.today():%d %b %Y} on the project desktop (Docker Desktop + Ollama, Qwen3-8B)."


def shot_isolation():
    cmd = ["docker", "compose", "run", "--rm", "agent", "python", "src/isolation_check.py"]
    lines = [PROMPT + "docker compose run --rm agent python src/isolation_check.py"] + run(cmd)
    render("isolation", "Windows PowerShell: the agent's container checks its own isolation", lines, [
        (r"non-root user", GREEN, "not root"),
        (r"all capabilities dropped", GREEN, "no privileges"),
        (r"root filesystem read-only", GREEN, "read-only"),
        (r"no direct internet \(1\.1", GREEN, "no internet"),
        (r"gateway blocks model management", GREEN, "gateway: chat only"),
        (r"16/16", YELLOW, "all 16 pass"),
    ], stamp())


def shot_container():
    names = run(["docker", "ps", "--format", "{{.Names}}"])
    probe = None
    target = next((n for n in names if n.startswith("run_")), None)
    if target is None:  # no run in progress: start a short-lived agent container to inspect
        probe = "evidence_probe"
        subprocess.run(["docker", "compose", "run", "-d", "--name", probe, "agent", "python", "-c",
                        "import time; time.sleep(120)"], cwd=SANDBOX, capture_output=True)
        target = probe
    fmt = ("user={{.Config.User}}  read-only={{.HostConfig.ReadonlyRootfs}}  "
           "capabilities dropped={{.HostConfig.CapDrop}}  memory={{.HostConfig.Memory}}")
    net = "{{range $k,$v := .NetworkSettings.Networks}}network={{$k}}{{end}}"
    lines = [PROMPT + 'docker ps --format "table {{.Names}}\\t{{.Image}}\\t{{.Status}}"']
    lines += run(["docker", "ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}"])
    lines += ["", PROMPT + f"docker inspect {target} --format \"user=... read-only=... ...\""]
    lines += run(["docker", "inspect", target, "--format", fmt]) + run(["docker", "inspect", target, "--format", net])
    lines += ["", PROMPT + 'docker network inspect sandbox_sandbox_internal --format "Internal={{.Internal}}"']
    lines += run(["docker", "network", "inspect", "sandbox_sandbox_internal", "--format", "Internal={{.Internal}}"])
    if probe:
        subprocess.run(["docker", "rm", "-f", probe], capture_output=True)
    render("container", "Windows PowerShell: the agent runs in a locked-down Docker container", lines, [
        (r"email-agent-sandbox", BLUE, "agent container"),
        (r"nginx-unprivileged", BLUE, "gateway"),
        (r"read-only=true", GREEN, "non-root, read-only"),
        (r"^network=", GREEN, "internal network only"),
        (r"^Internal=true", GREEN, "no route out"),
    ], stamp())


def code_lines(path: Path, anchor: str, before: int, after: int) -> tuple[int, list[str]]:
    src = path.read_text(encoding="utf-8").splitlines()
    i = next(n for n, l in enumerate(src) if anchor in l)
    block = src[i - before:i + after + 1]
    return i + 1 - before, textwrap.dedent("\n".join(block)).splitlines()  # method-body indentation dropped


def shot_rules():
    path = SANDBOX / "src" / "defenses.py"
    lines = []
    for title, anchor in (("D2 policy checks: is the tool on this task's list?", 'if tool not in policy.get("tools", [])'),
                          ("D1h provenance tracking: did the user ask for this action?",
                           "if not any(re.search(p, user) for p in INTENT[tool])")):
        start, src = code_lines(path, anchor, 0, 1)
        lines += [f"# {title}"]
        lines += [f"{start + k:>4}  {l}" for k, l in enumerate(src)] + [""]
    render("rules", "sandbox/src/defenses.py (frozen, tag defenses-frozen-v1)", lines[:-1], [
        (r'tool not in policy.get\("tools"', GREEN, ""),
        (r"re.search\(p, user\) for p in INTENT", GREEN, ""),
    ], "Plain code, no AI: the two rules that fired in the demo.")


def demo_lines(extra: list[str]) -> list[str]:
    cmd = ["docker", "compose", "run", "--rm", "agent", "python", "src/demo.py", *extra]
    return [PROMPT + "docker compose run --rm agent python src/demo.py " + " ".join(extra)] + run(cmd)


DEMO_BOXES = [(r"ALLOWED", RED, ""), (r"HIJACKED", RED, ""), (r"BLOCKED", GREEN, ""), (r"did not follow", GREEN, ""),
              (r"own task: done", BLUE, ""), (r"^Summary", YELLOW, "")]


def shot_demo():
    render("demo", "Windows PowerShell: one poisoned email, four agents (live model)", demo_lines(["--live"]),
           DEMO_BOXES, stamp())


def shot_demo_oracle():
    render("demo_oracle", "Windows PowerShell: one poisoned email, four agents (scripted agent)",
           demo_lines(["--oracle"]), DEMO_BOXES, "Scripted agent that obeys the attack (--oracle); no model.")


def shot_camel():
    mode = os.environ.get("CAMEL_SHOT_MODE", "--live")
    render("camel", "Windows PowerShell: the same gate around a CAMEL-AI agent",
           demo_lines([mode, "--agent", "camel"]),
           [(r"agent: CAMEL-AI", YELLOW, "")] + DEMO_BOXES,
           stamp() if mode == "--live" else "Scripted agent that obeys the attack (--oracle); no model.")


def compact(name: str, title: str):
    """A large-print excerpt of an already captured demo shot (evidence/<name>.txt), for projection: the
    command, each configuration's header, the attacker's action and the gate's decision, the verdicts and the
    summary. No rerun: the lines are copied from the capture, with the step lines in between left out."""
    src = (OUT / f"{name}.txt").read_text(encoding="utf-8").splitlines()
    keep = []
    for l in src:
        if l.startswith(PROMPT):
            keep.append("$ " + l[len(PROMPT):].replace("docker compose run --rm agent ", "").strip())
        elif l.startswith("Mode:"):
            keep.append(l)
        elif l.startswith("──"):
            keep += ["", l.rstrip("─ ")]
        elif l.startswith("Summary"):
            keep += ["", l]
        elif re.search(r"ALLOWED|BLOCKED|^\s+→", l):
            keep.append(re.sub(r"^\s+\d+\.\s+", "   ", l))
    keep = [l for l in keep if "own task" not in l]  # one blue line per config is enough on a slide: keep verdicts
    tail = [l for l in src if "own task: done" in l]
    keep.append(f"   Alex's own task done in {len(tail)} of {sum(l.startswith('──') for l in src)} configurations")
    render(f"{name}_compact", title, keep, [(r"ALLOWED", RED, ""), (r"HIJACKED", RED, ""), (r"BLOCKED", GREEN, ""),
                                            (r"did not follow", GREEN, ""), (r"own task done", BLUE, ""),
                                            (r"^Summary", YELLOW, "")],
           "Excerpt: step lines left out. Full output: rerun the command.", size=22)


SHOTS = {"isolation": shot_isolation, "container": shot_container, "rules": shot_rules, "demo": shot_demo,
         "demo_oracle": shot_demo_oracle, "camel": shot_camel,
         "demo_compact": lambda: compact("demo", "Live run, key lines: one poisoned email, four agents"),
         "camel_compact": lambda: compact("camel", "Live run, key lines: the same gate around a CAMEL-AI agent")}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("shots", nargs="*", default=list(SHOTS), choices=list(SHOTS))
    for name in ap.parse_args().shots:
        SHOTS[name]()
    sys.exit(0)
