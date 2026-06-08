mod commands;
mod menu;
mod sidecar;

use sidecar::Sidecar;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Spawn the Python bridge sidecar and keep it in app state.
            let handle = app.handle();
            let sidecar = Sidecar::spawn(handle)?;
            app.manage(sidecar);

            // Native menu.
            let m = menu::build_menu(handle)?;
            app.set_menu(m)?;

            Ok(())
        })
        .on_menu_event(|app, event| {
            menu::handle_menu_event(app, event.id().as_ref());
        })
        .invoke_handler(tauri::generate_handler![commands::ipc_request])
        .run(tauri::generate_context!())
        .expect("error while running InClave");
}
