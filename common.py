"""Tiny MCP-ish client helpers. stdlib only."""
import json, urllib.request

def call(port, method, params=None, token=None, client=None):
    """One stateless request. No session, no handshake — each call stands alone."""
    params = dict(params or {})
    meta = {}
    if client:
        meta["io.modelcontextprotocol/clientInfo"] = client
    if meta:
        params["_meta"] = meta
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", data=body,
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["result"]

def charges(store="/tmp/mcp_tasks.db"):
    import sqlite3
    c = sqlite3.connect(store); c.row_factory = sqlite3.Row
    rows = [dict(x) for x in c.execute("SELECT * FROM charges ORDER BY id")]
    c.close(); return rows

def line(): print("-" * 64)
