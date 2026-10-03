#!/usr/bin/env python3
"""
A tiny, deliberately-vulnerable MCP-shaped simulator:
  - stateless transport: no initialize handshake, no Mcp-Session-Id
  - protocol metadata is self-reported; authenticated identity is separate
  - cross-call state is stored server-side and referenced by task handles

It is INTENTIONALLY insecure in a few specific ways so the PoCs can show what
bites. Each weakness is flagged with a `# VULN:` comment and the fix.

Run one (or several) instances pointed at a shared store:
    python3 server.py --port 9001 --store /tmp/mcp_tasks.db
    python3 server.py --port 9002 --store /tmp/mcp_tasks.db   # same store = "any instance serves any request"

This is not a conformant MCP implementation. See docs/spec-scope.md.
stdlib only. Python 3.11+.
"""
import argparse, json, os, sqlite3, threading, time, secrets, http.server, socketserver
from pathlib import Path

from common import port_number

STORE = None
WEAK_HANDLES = False
INSTANCE = "?"

# --- store -----------------------------------------------------------------
def db():
    c = sqlite3.connect(STORE, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init_store():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS tasks(
      task_id TEXT PRIMARY KEY,
      owner   TEXT,            -- the principal who created it
      tenant  TEXT,
      status  TEXT,            -- working|input_required|completed|failed|cancelled
      tool    TEXT,
      args    TEXT,
      result  TEXT,
      cancel_requested INTEGER DEFAULT 0,
      created REAL
    );
    CREATE TABLE IF NOT EXISTS charges(   -- a real-world side effect
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id TEXT, tenant TEXT, amount REAL, note TEXT, ts REAL
    );
    """)
    c.commit(); c.close()

def mint_handle():
    if WEAK_HANDLES:
        # VULN: guessable handle. Fix: secrets.token_urlsafe(32) (>=128 bits).
        # INSERT's SQLite rowid becomes the counter inside the creation transaction.
        return None
    return "task_" + secrets.token_urlsafe(24)

# --- task worker -----------------------------------------------------------
def run_task(task_id):
    """Simulate slow work that ends in a side effect (a 'charge')."""
    for _ in range(10):
        time.sleep(0.4)
        c = db()
        row = c.execute("SELECT cancel_requested FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        c.close()
        # VULN: cancel is cooperative AND we ignore it. tasks/cancel only ack's;
        # the worker never actually checks-and-aborts, so the side effect below
        # still fires. Fix: honor cancel_requested here AND make the side effect
        # transactional with the cancel check.
        # (left intentionally not-aborting to demo the phantom kill switch)
    c = db()
    t = c.execute("SELECT tenant,args,status FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    if t:
        tenant, args, status = t
        a = json.loads(args or "{}")
        amount = a.get("amount", 42.00)
        # side effect happens regardless of a prior "cancel"
        c.execute("INSERT INTO charges(task_id,tenant,amount,note,ts) VALUES(?,?,?,?,?)",
                  (task_id, tenant, amount, a.get("note", "order"), time.time()))
        # only flip to completed if it wasn't already marked cancelled
        c.execute("UPDATE tasks SET result=?, status=CASE WHEN status='cancelled' THEN 'cancelled' ELSE 'completed' END WHERE task_id=?",
                  (json.dumps({"charged": amount, "note": a.get("note", "order")}), task_id))
        c.commit()
    c.close()

# --- rpc handlers ----------------------------------------------------------
def identity(req, headers):
    """Who is calling? Bearer token -> principal; _meta carries client info.
    VULN: we trust _meta clientInfo for the tenant when no token is present."""
    auth = headers.get("Authorization", "")
    meta = (req.get("params", {}) or {}).get("_meta", {}) or {}
    token = auth.replace("Bearer ", "").strip()
    principals = {"tok-alice": ("alice", "acme"), "tok-bob": ("bob", "globex")}
    if token in principals:
        return principals[token]
    ci = meta.get("io.modelcontextprotocol/clientInfo", {})
    return (ci.get("name", "anon"), ci.get("tenant", "public"))

def handle_rpc(req, headers):
    method = req.get("method")
    params = req.get("params", {}) or {}
    who, tenant = identity(req, headers)

    if method == "server/discover":
        return {"protocolVersions": ["2026-07-28"], "capabilities": {"extensions": ["io.modelcontextprotocol/tasks"]},
                "serverInfo": {"name": "vuln-demo", "instance": INSTANCE},
                "demo": {"store": STORE, "weak_handles": WEAK_HANDLES}}

    if method == "tools/call":
        tool = params.get("name")
        args = params.get("arguments", {})
        tid = mint_handle()
        c = db()
        inserted = c.execute("INSERT INTO tasks(task_id,owner,tenant,status,tool,args,created) VALUES(?,?,?,?,?,?,?)",
                             (tid, who, tenant, "working", tool, json.dumps(args), time.time()))
        if WEAK_HANDLES:
            tid = f"task_{inserted.lastrowid:04d}"
            c.execute("UPDATE tasks SET task_id=? WHERE rowid=?", (tid, inserted.lastrowid))
        c.commit(); c.close()
        threading.Thread(target=run_task, args=(tid,), daemon=True).start()
        return {"resultType": "task", "task": {"taskId": tid, "status": "working"}}

    if method in ("tasks/get", "tasks/update", "tasks/cancel"):
        tid = params.get("taskId")
        c = db()
        row = c.execute("SELECT task_id,owner,tenant,status,result,cancel_requested FROM tasks WHERE task_id=?", (tid,)).fetchone()
        # VULN: NO check that `who`/`tenant` matches the task's owner/tenant.
        # Any caller holding the handle can read/drive it. Fix: enforce
        # row.owner == who (and tenant) on EVERY task-related request.
        if not row:
            c.close(); return {"error": {"code": -32602, "message": "no such task"}}
        _, owner, ttenant, status, result, canceled = row
        if method == "tasks/cancel":
            c.execute("UPDATE tasks SET cancel_requested=1, status='cancelled' WHERE task_id=?", (tid,))
            c.commit(); c.close()
            return {"ack": True, "note": "cancellation requested (cooperative)"}
        c.close()
        return {"resultType": "task", "task": {"taskId": tid, "owner": owner, "tenant": ttenant,
                "status": status, "result": json.loads(result) if result else None}}

    return {"error": {"code": -32601, "message": f"unknown method {method}"}}

# --- http ------------------------------------------------------------------
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or "{}")
        except Exception:
            req = {}
        # NOTE: we never look for Mcp-Session-Id. Statelessness by design.
        out = handle_rpc(req, self.headers)
        body = json.dumps({"jsonrpc": "2.0", "id": req.get("id"),
                           "result": out, "_meta": {"io.modelcontextprotocol/serverInfo": {"instance": INSTANCE}}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

class Threaded(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=port_number, default=os.getenv("MCP_DEMO_PORT", "9001"))
    ap.add_argument("--store", default=os.getenv("MCP_DEMO_STORE", "/tmp/mcp_tasks.db"))
    ap.add_argument("--weak-handles", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="require a new store; refuse to overwrite existing data")
    ap.add_argument("--ready-file", type=Path, help=argparse.SUPPRESS)
    a = ap.parse_args()
    STORE = str(Path(a.store).resolve()); WEAK_HANDLES = a.weak_handles
    # Bind before opening SQLite. A stale process must never cause a database reset.
    try:
        httpd = Threaded(("127.0.0.1", a.port), H)
    except OSError as error:
        ap.exit(1, f"Cannot bind loopback port {a.port}: {error}. Stop that server or choose another port.\n")
    try:
        if a.fresh:
            try:
                # Atomic exclusive creation also protects against another --fresh starter.
                fd = os.open(STORE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError:
                ap.exit(1, "Refusing --fresh on an existing store. Choose a new --store path or use demo.py.\n")
        INSTANCE = f"srv:{httpd.server_port}"
        init_store()
        if a.ready_file:
            a.ready_file.write_text(json.dumps({
                "port": httpd.server_port, "store": STORE, "weak_handles": WEAK_HANDLES,
            }))
        print(f"[{INSTANCE}] vulnerable local simulator; store={STORE} weak_handles={WEAK_HANDLES}", flush=True)
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, sqlite3.Error) as error:
        ap.exit(1, f"Cannot start demo server: {error}\n")
    finally:
        httpd.server_close()
