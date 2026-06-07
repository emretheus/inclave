# inclave-bridge

The desktop **sidecar**: a headless JSON-RPC 2.0 server that the Tauri shell
spawns and supervises. It re-uses the InClave engine (`inclave_core`,
`inclave_ollama`, `inclave_sandbox`, and the `chat_engine` orchestration from
`inclave_cli`) and exposes it to the React frontend over the sidecar's stdio.

It opens **no listening socket**. The only network connection ever made is the
engine's own talk to the local Ollama daemon at `127.0.0.1:11434`.

## Protocol

- **Transport:** newline-delimited JSON-RPC 2.0 over stdin/stdout.
- **Requests** (frontend → sidecar): `config.get`, `models.list`, `chat.send`, …
- **Notifications** (sidecar → frontend): streamed events with no `id` —
  `chat.token`, `chat.run_output`, `models.pull_progress`, …

See `protocol.py` for the canonical method + event list. The TypeScript types
and zod validators in `packages-js/ipc-contract` are generated from the schema
exported by `scripts/export_schema.py`.

## Run standalone (for debugging)

```bash
uv run inclave-bridge   # reads JSON-RPC lines on stdin, writes on stdout
```

Example session:

```json
{"jsonrpc":"2.0","id":1,"method":"system.status"}
```
