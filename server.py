#!/usr/bin/env python3
"""
A tiny, deliberately-vulnerable MCP server shaped like the 2026-07-28 spec:
  - stateless transport: no initialize handshake, no Mcp-Session-Id
  - every request self-describes identity in _meta
  - cross-call state lives in server-minted handles (the Tasks extension)

It is INTENTIONALLY insecure in a few specific ways so the PoCs can show what
bites. Each weakness is flagged with a `# VULN:` comment and the fix.

Run one (or several) instances pointed at a shared store:
    python3 server.py --port 9001 --store /tmp/mcp_tasks.db
    python3 server.py --port 9002 --store /tmp/mcp_tasks.db   # same store = "any instance serves any request"

stdlib only. Python 3.11+.
"""
import argparse, json, os, sqlite3, threading, time, secrets, http.server, socketserver

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

_seq = 0
_seq_lock = threading.Lock()
def mint_handle():
    global _seq
    if WEAK_HANDLES:
        # VULN: guessable handle. Fix: secrets.token_urlsafe(32) (>=128 bits).
        with _seq_lock:
            _seq += 1
            return f"task_{int(time.time())}_{_seq:04d}"
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
                "serverInfo": {"name": "vuln-demo", "instance": INSTANCE}}

    if method == "tools/call":
        tool = params.get("name")
        args = params.get("arguments", {})
        tid = mint_handle()
        c = db()
        c.execute("INSERT INTO tasks(task_id,owner,tenant,status,tool,args,created) VALUES(?,?,?,?,?,?,?)",
                  (tid, who, tenant, "working", tool, json.dumps(args), time.time()))
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
    ap.add_argument("--port", type=int, default=9001)
    ap.add_argument("--store", default="/tmp/mcp_tasks.db")
    ap.add_argument("--weak-handles", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="wipe the store first")
    a = ap.parse_args()
    STORE = a.store; WEAK_HANDLES = a.weak_handles; INSTANCE = f"srv:{a.port}"
    if a.fresh and os.path.exists(STORE):
        for suf in ("", "-wal", "-shm"):
            try: os.remove(STORE + suf)
            except OSError: pass
    init_store()
    print(f"[{INSTANCE}] stateless MCP (vuln demo) on :{a.port} store={STORE} weak_handles={WEAK_HANDLES}")
    Threaded(("127.0.0.1", a.port), H).serve_forever()
