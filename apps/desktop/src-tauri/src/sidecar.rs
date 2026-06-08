//! Spawns and supervises the Python bridge sidecar, speaking newline-delimited
//! JSON-RPC over its stdio. Responses are correlated to requests by id;
//! notifications (no id) are forwarded to the webview as `bridge://event`.
//!
//! There is no listening socket — the only pipe is the child's stdin/stdout,
//! which keeps the privacy story airtight.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Mutex};

use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::oneshot;

/// A pending request awaiting its response, keyed by JSON-RPC id.
type Pending = Arc<Mutex<HashMap<i64, oneshot::Sender<Value>>>>;

/// How to launch the sidecar: (program, args, extra env vars).
type LaunchSpec = (String, Vec<String>, Vec<(String, String)>);

pub struct Sidecar {
    stdin: Mutex<ChildStdin>,
    pending: Pending,
    next_id: AtomicI64,
    _child: Mutex<Child>,
}

impl Sidecar {
    /// Spawn the sidecar. In dev we run it via `uv run inclave-bridge`; in a
    /// bundled app we run the packaged `inclave-bridge` binary next to the
    /// executable. INCLAVE_SANDBOX_RUNTIME is set so the sandbox can locate its
    /// packaged Python runtime.
    pub fn spawn(app: &AppHandle) -> Result<Self> {
        let (program, args, env) = resolve_command(app)?;

        let mut cmd = Command::new(program);
        cmd.args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());
        for (k, v) in env {
            cmd.env(k, v);
        }

        let mut child = cmd
            .spawn()
            .map_err(|e| anyhow!("failed to spawn sidecar: {e}"))?;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| anyhow!("no sidecar stdin"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| anyhow!("no sidecar stdout"))?;

        let pending: Pending = Arc::new(Mutex::new(HashMap::new()));

        // Reader thread: parse every line, route responses vs notifications.
        {
            let pending = pending.clone();
            let app = app.clone();
            std::thread::spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines() {
                    let Ok(line) = line else { break };
                    if line.trim().is_empty() {
                        continue;
                    }
                    let Ok(frame): Result<Value, _> = serde_json::from_str(&line) else {
                        continue;
                    };
                    route_frame(&app, &pending, frame);
                }
            });
        }

        Ok(Sidecar {
            stdin: Mutex::new(stdin),
            pending,
            next_id: AtomicI64::new(1),
            _child: Mutex::new(child),
        })
    }

    /// Send a request and await its result. Streaming methods emit notifications
    /// via the reader thread before this resolves with the final result.
    pub async fn request(&self, method: &str, params: Value) -> Result<Value> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        let (tx, rx) = oneshot::channel();
        self.pending.lock().unwrap().insert(id, tx);

        let frame = json!({ "jsonrpc": "2.0", "id": id, "method": method, "params": params });
        let line = serde_json::to_string(&frame)? + "\n";
        {
            let mut stdin = self.stdin.lock().unwrap();
            stdin.write_all(line.as_bytes())?;
            stdin.flush()?;
        }

        let resp = rx
            .await
            .map_err(|_| anyhow!("sidecar closed before responding"))?;
        if let Some(err) = resp.get("error") {
            return Err(anyhow!(err.to_string()));
        }
        Ok(resp.get("result").cloned().unwrap_or(Value::Null))
    }
}

fn route_frame(app: &AppHandle, pending: &Pending, frame: Value) {
    if let Some(id) = frame.get("id").and_then(|v| v.as_i64()) {
        // Response to a request.
        if let Some(tx) = pending.lock().unwrap().remove(&id) {
            let _ = tx.send(frame);
        }
    } else if let Some(method) = frame.get("method").and_then(|v| v.as_str()) {
        // Notification → forward to the webview.
        let payload = json!({
            "method": method,
            "params": frame.get("params").cloned().unwrap_or(Value::Null),
        });
        let _ = app.emit("bridge://event", payload);
    }
}

/// Decide how to launch the sidecar based on whether we're bundled.
fn resolve_command(app: &AppHandle) -> Result<LaunchSpec> {
    // Bundled: a sidecar binary sits in the resource dir; the sandbox runtime is
    // bundled alongside it.
    if let Ok(resource_dir) = app.path().resource_dir() {
        let bin = resource_dir.join("inclave-bridge");
        if bin.exists() {
            let runtime = resource_dir.join("sandbox-runtime");
            let env = vec![(
                "INCLAVE_SANDBOX_RUNTIME".to_string(),
                runtime.to_string_lossy().to_string(),
            )];
            return Ok((bin.to_string_lossy().to_string(), vec![], env));
        }
    }

    // Dev fallback: run via uv from the repo root.
    Ok((
        "uv".to_string(),
        vec!["run".into(), "inclave-bridge".into()],
        vec![],
    ))
}
