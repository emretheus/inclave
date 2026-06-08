//! Native macOS menu bar with real accelerators. Menu actions emit events the
//! webview listens for (mirroring the in-app keyboard shortcuts).

use tauri::menu::{AboutMetadata, Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, Emitter, Manager, Runtime};

pub fn build_menu<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    let pkg = app.package_info().name.clone();

    let app_menu = Submenu::with_items(
        app,
        &pkg,
        true,
        &[
            &PredefinedMenuItem::about(app, Some(&pkg), Some(AboutMetadata::default()))?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "settings", "Settings…", true, Some("Cmd+,"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::hide(app, None)?,
            &PredefinedMenuItem::quit(app, None)?,
        ],
    )?;

    let file_menu = Submenu::with_items(
        app,
        "File",
        true,
        &[
            &MenuItem::with_id(app, "new_chat", "New Chat", true, Some("Cmd+N"))?,
            &MenuItem::with_id(app, "add_files", "Add Files…", true, Some("Cmd+O"))?,
        ],
    )?;

    let edit_menu = Submenu::with_items(
        app,
        "Edit",
        true,
        &[
            &PredefinedMenuItem::undo(app, None)?,
            &PredefinedMenuItem::redo(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::cut(app, None)?,
            &PredefinedMenuItem::copy(app, None)?,
            &PredefinedMenuItem::paste(app, None)?,
            &PredefinedMenuItem::select_all(app, None)?,
        ],
    )?;

    let chat_menu = Submenu::with_items(
        app,
        "Chat",
        true,
        &[
            &MenuItem::with_id(app, "run_last", "Run Last Code", true, Some("Cmd+Return"))?,
            &MenuItem::with_id(app, "palette", "Command Palette", true, Some("Cmd+K"))?,
        ],
    )?;

    let window_menu = Submenu::with_items(
        app,
        "Window",
        true,
        &[
            &PredefinedMenuItem::minimize(app, None)?,
            &PredefinedMenuItem::fullscreen(app, None)?,
        ],
    )?;

    Menu::with_items(
        app,
        &[&app_menu, &file_menu, &edit_menu, &chat_menu, &window_menu],
    )
}

pub fn handle_menu_event<R: Runtime>(app: &AppHandle<R>, id: &str) {
    // The webview maps these to the same handlers as its keyboard shortcuts.
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.emit("menu://action", id);
    }
}
