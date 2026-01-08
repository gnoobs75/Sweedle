mod commands;
mod utils;

use commands::{file_ops, mesh_ops, model_loader};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            // Model loading commands
            model_loader::analyze_model,
            model_loader::load_model_data,
            model_loader::get_model_bounds,
            // Mesh operations
            mesh_ops::generate_lod,
            mesh_ops::optimize_mesh,
            mesh_ops::calculate_mesh_stats,
            // File operations
            file_ops::read_file_chunked,
            file_ops::get_file_info,
            file_ops::list_storage_assets,
            file_ops::watch_directory,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
