"""sandbox.py - run model-written Python (B, B+) or SPARQL (C) in a subprocess.

Best-effort isolation against accidents, NOT a security boundary:
- fresh temp dir as cwd, containing only the graph file (never answers.json or truth.py)
- python -I (isolated mode), scrubbed environment (no API keys), wall-clock timeout
- socket and subprocess creation disabled inside the process by a prelude (bypassable by
  a determined program; there is no OS-level network isolation on this machine)
- stdout/stderr truncated
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
TIMEOUT_S = 60
MAX_OUT = 4000

PRELUDE = '''import socket as _s, subprocess as _sp, os as _os
def _blocked(*a, **k):
    raise OSError("network and subprocesses are disabled in this sandbox")
_s.socket.connect = _s.socket.connect_ex = _blocked
_s.create_connection = _s.getaddrinfo = _blocked
_sp.Popen = _sp.run = _sp.call = _sp.check_output = _os.system = _blocked
del _s, _sp, _os
'''


def _env():
    keep = ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "PATH")  # minimum Windows needs to start Python
    return {k: os.environ[k] for k in keep if k in os.environ}


def _run(args, files, stdin=None):
    tmp = Path(tempfile.mkdtemp(prefix="br_sandbox_"))
    try:
        for name, src in files.items():
            if isinstance(src, Path):
                shutil.copy(src, tmp / name)
            else:
                (tmp / name).write_text(src, encoding="utf-8")
        p = subprocess.run([sys.executable, "-I", *args], cwd=tmp, env=_env(), input=stdin,
                           capture_output=True, text=True, timeout=TIMEOUT_S, encoding="utf-8")
        return dict(returncode=p.returncode, timeout=False,
                    stdout=p.stdout[-MAX_OUT:], stderr=p.stderr[-MAX_OUT:])
    except subprocess.TimeoutExpired as e:
        tail = lambda s: (s.decode() if isinstance(s, bytes) else s or "")[-MAX_OUT:]
        return dict(returncode=None, timeout=True, stdout=tail(e.stdout), stderr=tail(e.stderr))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_python(code, size):
    """B/B+: the program sees graph.json in its cwd and nothing else from this repo."""
    return _run(["main.py"], {"graph.json": DATA / f"graph_{size}.json", "main.py": PRELUDE + code})


SPARQL_RUNNER = '''import json, sys
from decimal import Decimal
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from rdflib.plugins.sparql import prepareQuery
EX = Namespace("http://example.org/br#")
NS = {"ex": EX, "rdf": RDF, "rdfs": RDFS, "owl": OWL, "xsd": XSD}
query = sys.stdin.read()
try:
    prepared = prepareQuery(query, initNs=NS)
except Exception as e:
    print(json.dumps({"error_kind": "parse", "error": f"{type(e).__name__}: {e}"})); sys.exit(0)
g = Graph()
g.parse("data.ttl"); g.parse("schema.ttl")
def val(x):
    if x is None: return None
    if isinstance(x, URIRef): return str(x).removeprefix(str(EX))
    v = x.toPython() if isinstance(x, Literal) else str(x)
    if isinstance(v, Decimal): return float(v)
    return v if isinstance(v, (bool, int, float, str)) else str(v)
try:
    res = g.query(prepared)
    if res.type == "ASK":
        out = {"kind": "ask", "value": bool(res.askAnswer)}
    else:
        rows = [[val(c) for c in row] for row in res]
        out = {"kind": "select", "vars": [str(v) for v in res.vars], "rows": rows}
except Exception as e:
    out = {"error_kind": "execution", "error": f"{type(e).__name__}: {e}"}
print(json.dumps(out))
'''


def run_sparql(query, size):
    """C: execute against data + schema. Returns the runner's JSON result or an error dict."""
    r = _run(["runner.py"], {"runner.py": SPARQL_RUNNER, "data.ttl": DATA / f"graph_{size}.ttl",
                             "schema.ttl": ROOT / "schema.ttl"}, stdin=query)
    if r["timeout"]:
        return {"error_kind": "timeout", "error": f"query timed out after {TIMEOUT_S} s"}
    try:
        return json.loads(r["stdout"].strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"error_kind": "execution", "error": r["stderr"][-1500:] or "runner produced no output"}
