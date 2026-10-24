"""Verify the sandbox is actually isolated. Run INSIDE the agent container:

    docker compose run --rm agent python src/isolation_check.py

Exit code 0 only if every hard check passes. "gateway reachable" is a WARN when
host Ollama isn't running, because isolation is still intact in that case.
"""
from __future__ import annotations

import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY = os.environ.get("OLLAMA_BASE_URL", "http://llm-gateway:11434").rstrip("/")
results: list[tuple[str, str, str]] = []


def record(name: str, ok: bool, detail: str = "", warn_only: bool = False) -> None:
    results.append((name, "PASS" if ok else ("WARN" if warn_only else "FAIL"), detail))


def can_connect(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def status(path: str, method: str = "GET") -> int:
    req = urllib.request.Request(GATEWAY + path, method=method,
                                 data=b"{}" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError:
        return -1


def proc_status_field(field: str) -> str:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(field + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def writable(path: str) -> bool:
    try:
        p = Path(path) / ".isolation_probe"
        p.write_text("x")
        p.unlink()
        return True
    except OSError:
        return False


# 1. Identity and privileges
record("non-root user", os.geteuid() != 0, f"uid={os.geteuid()}")
cap_eff = proc_status_field("CapEff")
record("all capabilities dropped", int(cap_eff or "1", 16) == 0, f"CapEff={cap_eff}")
record("no_new_privs set", proc_status_field("NoNewPrivs") == "1")

# 2. Filesystem
record("root filesystem read-only", not writable("/") and not writable("/etc"))
record("code directory read-only", not writable(str(Path(__file__).resolve().parent)))
record("benchmark mount read-only", not writable("/data/benchmark"))
record("results mount writable", writable("/data/results"))
record("docker socket not mounted", not Path("/var/run/docker.sock").exists())

# 3. Network egress must fail
record("no direct internet (1.1.1.1:443)", not can_connect("1.1.1.1", 443))
record("no direct internet (8.8.8.8:53)", not can_connect("8.8.8.8", 53))
try:
    socket.getaddrinfo("pypi.org", 443)
    dns_ok = True
except OSError:
    dns_ok = False
record("no external DNS (pypi.org)", not dns_ok)
record("host not directly reachable", not can_connect("host.docker.internal", 11434))

# 4. Gateway: only the model API is reachable
code = status("/api/version")
record("gateway reachable (/api/version)", code == 200,
       f"HTTP {code} (502/-1 means host Ollama is not running)", warn_only=True)
record("gateway blocks model management (/api/pull)", status("/api/pull", "POST") == 403)
record("gateway blocks model deletion (/api/delete)", status("/api/delete", "POST") == 403)
record("gateway blocks other paths (/)", status("/") == 403)

width = max(len(n) for n, _, _ in results)
for name, verdict, detail in results:
    print(f"{verdict:4}  {name:<{width}}  {detail}")
failed = [n for n, v, _ in results if v == "FAIL"]
print(f"\n{len(results) - len(failed)}/{len(results)} checks not failed"
      + (f"; FAILED: {', '.join(failed)}" if failed else "; sandbox isolation OK"))
sys.exit(1 if failed else 0)
