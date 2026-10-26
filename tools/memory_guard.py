"""Host memory guard for long sandbox runs (Windows, stdlib only).

    Start-Process pythonw -ArgumentList 'tools/memory_guard.py','--container','run_x'   (PowerShell, project root)

Every --poll seconds it reads free physical RAM and Ollama's working set. When free RAM is below --low-gb
or Ollama has grown past --max-ollama-gb, it writes sandbox/results/progress/memory_low.flag (a timestamp,
renewed every poll); once free RAM is above --ok-gb and Ollama is back under its cap, it removes it.
Thresholds: on this 16 GB host a freshly loaded qwen3:8b alone holds ~5.5 GB and leaves ~2.5 GB free
(measured 26 Oct), so the defaults sit just below that state and only fire on growth or other load.
The AgentDojo runner checks the flag between episodes, unloads the model and waits, so Ollama's growing
runner process (Vulkan on Windows) gives its memory back before Windows runs out. It also logs time,
free RAM and Ollama's working set to sandbox/results/progress/memory_<label>.csv (numbers only) and
exits once the container has stopped. Started with Start-Process it is not a child of the Claude Code
shell, so that shell's memory reaper does not stop it.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

PROGRESS = Path(__file__).resolve().parents[1] / "sandbox" / "results" / "progress"
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW: no console flashes under pythonw


class MemoryStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_gb() -> float:
    m = MemoryStatus()
    m.dwLength = ctypes.sizeof(MemoryStatus)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2 ** 30


def ollama_gb() -> float:
    """Working set of the Ollama and llama processes, from tasklist (e.g. '6,123,456 K')."""
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         creationflags=NO_WINDOW).stdout
    kb = sum(int("".join(c for c in row[4] if c.isdigit()) or 0)
             for row in csv.reader(out.splitlines()) if len(row) > 4 and row[0].lower().startswith(("ollama", "llama")))
    return kb / 2 ** 20


def running(container: str) -> bool:
    r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container], capture_output=True,
                       text=True, creationflags=NO_WINDOW)
    return r.returncode == 0 and r.stdout.strip() == "true"


def step(flag: Path, free: float, ollama: float, low: float, ok: float, max_ollama: float) -> bool:
    """Set, renew or clear the flag for this reading; True if it is set afterwards."""
    if free < low or ollama > max_ollama or (flag.exists() and free <= ok):
        flag.write_text(dt.datetime.now().isoformat(), encoding="ascii")  # renewed: proves the guard is alive
    elif flag.exists():
        flag.unlink()
    return flag.exists()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--low-gb", type=float, default=2.0)
    ap.add_argument("--ok-gb", type=float, default=3.0)
    ap.add_argument("--max-ollama-gb", type=float, default=7.0)
    ap.add_argument("--poll", type=float, default=15.0)
    ap.add_argument("--label", default="")
    args = ap.parse_args(argv)
    PROGRESS.mkdir(parents=True, exist_ok=True)
    flag = PROGRESS / "memory_low.flag"
    log = PROGRESS / f"memory_{args.label or args.container}.csv"
    new = not log.exists()
    deadline = time.monotonic() + 120  # the container may not have started yet
    while not running(args.container) and time.monotonic() < deadline:
        time.sleep(5)
    with log.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "free_gb", "ollama_gb", "flag"])
        while running(args.container):
            free, ollama = free_gb(), ollama_gb()
            on = step(flag, free, ollama, args.low_gb, args.ok_gb, args.max_ollama_gb)
            w.writerow([dt.datetime.now().isoformat(timespec="seconds"), f"{free:.2f}", f"{ollama:.2f}", int(on)])
            f.flush()
            time.sleep(args.poll)
    flag.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
