# AI label remote-control worker

The Nature-Scribe transcription page can extract specimen-label text via two
backends: the **Anthropic API** (direct server-to-server) and the
**Remote (Claude session)** backend, which routes through a local worker
process that bridges the operator's existing Claude session.

This document covers operating the **remote worker**.

## Why a separate process?

- gunicorn workers shouldn't hold long-lived stdio handles or sockets to a
  Claude session — a single worker keeps the bridge state out of request
  handlers and de-duplicates concurrent requests for the same unit.
- Restarting Flask doesn't kill the Claude session.
- The worker can be replaced (subprocess → MCP → Agent SDK) without touching
  Flask code, as long as the JSON-over-socket protocol is preserved.

## Protocol

Unix-domain socket. One JSON request per connection, terminated by `\n`;
the worker writes one JSON reply terminated by `\n` and closes the
connection.

**Request:**

```json
{
  "image_b64": "<base64 of JPEG bytes>",
  "prompt_version": "label-v1",
  "model": null
}
```

**Reply (success):**

```json
{
  "text": "<raw label transcription>",
  "model": "claude-sonnet-4-6",
  "ms": 2340
}
```

**Reply (error):**

```json
{ "error": "<short message>" }
```

## Configuration

Three env vars (read by both Flask and the worker):

| Var | Default | Purpose |
|---|---|---|
| `AI_LABEL_REMOTE_SOCKET` | `/tmp/naturedb-ai-label.sock` | Unix-socket path |
| `AI_LABEL_REMOTE_TIMEOUT` | `60` | Flask waits this many seconds for a reply |
| `AI_LABEL_REMOTE_LOG_LEVEL` | `INFO` | Worker log level |

The socket is created with mode `0600` (same-user only). For multi-user
deployments, place the socket in a directory whose ACLs match your security
posture.

## Running the worker

The worker is **not** auto-started by Flask. Start it separately, using the
**same Python environment as the Flask app** (the `-m` runner imports
`app.__init__`, which transitively pulls in Flask + SQLAlchemy + the rest of
the project's deps):

```bash
# activate your venv first
source .venv/bin/activate    # or whatever activates your project env

# foreground (for development)
python -m app.services.ai.remote_worker

# background, capturing logs
nohup python -m app.services.ai.remote_worker \
  > /var/log/naturedb-ai-worker.log 2>&1 &
```

Stop it with `Ctrl-C` (SIGINT) or `kill <pid>` (SIGTERM); the worker
removes its socket file on clean shutdown.

### systemd unit (recommended for production)

```ini
# /etc/systemd/system/naturedb-ai-worker.service
[Unit]
Description=NatureDB AI label remote-control worker
After=network.target

[Service]
Type=simple
User=naturedb
EnvironmentFile=/etc/naturedb/ai.env
WorkingDirectory=/srv/naturedb
ExecStart=/srv/naturedb/.venv/bin/python -m app.services.ai.remote_worker
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now naturedb-ai-worker
sudo systemctl status naturedb-ai-worker
```

## Wiring up a real Claude bridge

The shipped worker has a **stub** `_call_claude()` that returns placeholder
text — useful for verifying the JS panel + socket plumbing without a real
Claude session. To make the worker actually transcribe labels, replace
`_call_claude()` in `app/services/ai/remote_worker.py`. Three options:

### Option 1: Spawn `claude` CLI as subprocess

Simplest if you have Claude Code installed and authenticated locally.

```python
import subprocess, tempfile, json
from app.services.ai.extractor import LABEL_SYSTEM_PROMPT

def _call_claude(image_bytes, prompt_version, model):
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(image_bytes)
        image_path = f.name
    try:
        proc = subprocess.run(
            ['claude', '--print', '--output-format', 'json'],
            input=f'{LABEL_SYSTEM_PROMPT}\n\nTranscribe @{image_path}',
            capture_output=True, text=True, timeout=90,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or 'claude CLI failed')
        out = json.loads(proc.stdout)
        return {'text': out.get('result', ''), 'model': out.get('model', 'claude-cli')}
    finally:
        import os; os.unlink(image_path)
```

### Option 2: Claude Agent SDK

Use the Python `claude_agent_sdk` to run a vision-capable session in-process.

### Option 3: MCP client

Connect to a Claude Code MCP endpoint (e.g. via the SDK's `MCPServer` API)
and call a custom transcribe tool. Most flexible for multi-tool workflows.

In all three cases, return a dict with at least `text` and `model`. The
worker handles framing, timing, and error reporting around your bridge.

## Health check

Flask exposes `GET /api/v1/scribe/ai/health` (no auth) which attempts a
non-blocking socket connect to the worker. The transcription panel calls
this once per page load and disables the "Remote (Claude session)" option
when `remote_available` is false.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Panel shows Remote disabled with "Remote backend unavailable" | Worker not running, or socket path mismatch | Start the worker; verify `AI_LABEL_REMOTE_SOCKET` matches in both processes |
| `503 remote_down` from `/ai/label` | Socket file missing | Same as above |
| `504 remote_timeout` | Bridge took >`AI_LABEL_REMOTE_TIMEOUT`s | Bump the timeout, or speed up `_call_claude` |
| Replies always say "[remote-worker stub]" | Default placeholder bridge in use | Replace `_call_claude` per "Wiring up a real Claude bridge" above |
| Worker crashes on second connection | Bridge implementation holds non-reentrant state | Audit `_call_claude` for thread/process safety; the worker itself is single-threaded |
