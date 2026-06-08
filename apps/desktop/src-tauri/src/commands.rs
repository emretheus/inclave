//! The single Tauri command the frontend uses to reach the sidecar. Keeping the
//! surface to one allow-listed command (`ipc_request`) is the trust boundary:
//! the webview cannot invoke arbitrary Rust or Python.

use serde_json::Value;
use tauri::State;

use crate::sidecar::Sidecar;

#[tauri::command]
pub async fn ipc_request(
    sidecar: State<'_, Sidecar>,
    method: String,
    params: Value,
) -> Result<Value, String> {
    sidecar
        .request(&method, params)
        .await
        .map_err(|e| e.to_string())
}
