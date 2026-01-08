use memmap2::Mmap;
use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::path::Path;
use std::time::SystemTime;
use tauri::command;
use walkdir::WalkDir;

/// Information about a file
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub path: String,
    pub name: String,
    pub extension: Option<String>,
    pub size_bytes: u64,
    pub created: Option<u64>,
    pub modified: Option<u64>,
    pub is_directory: bool,
}

/// Information about an asset in storage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageAsset {
    pub id: String,
    pub path: String,
    pub has_glb: bool,
    pub has_obj: bool,
    pub has_fbx: bool,
    pub has_thumbnail: bool,
    pub glb_size: Option<u64>,
    pub thumbnail_path: Option<String>,
}

/// Read file in chunks for streaming
#[command]
pub async fn read_file_chunked(
    path: String,
    offset: Option<u64>,
    length: Option<u64>,
) -> Result<Vec<u8>, String> {
    let path = Path::new(&path);

    if !path.exists() {
        return Err(format!("File not found: {}", path.display()));
    }

    let file = File::open(path).map_err(|e| format!("Failed to open file: {}", e))?;
    let mmap = unsafe { Mmap::map(&file) }.map_err(|e| format!("Failed to mmap file: {}", e))?;

    let start = offset.unwrap_or(0) as usize;
    let len = length.unwrap_or(mmap.len() as u64) as usize;
    let end = (start + len).min(mmap.len());

    if start >= mmap.len() {
        return Ok(vec![]);
    }

    Ok(mmap[start..end].to_vec())
}

/// Get detailed information about a file
#[command]
pub async fn get_file_info(path: String) -> Result<FileInfo, String> {
    let path_obj = Path::new(&path);

    if !path_obj.exists() {
        return Err(format!("File not found: {}", path));
    }

    let metadata = fs::metadata(path_obj).map_err(|e| format!("Failed to read metadata: {}", e))?;

    let name = path_obj
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();

    let extension = path_obj
        .extension()
        .map(|e| e.to_string_lossy().to_string());

    let created = metadata
        .created()
        .ok()
        .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
        .map(|d| d.as_secs());

    let modified = metadata
        .modified()
        .ok()
        .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
        .map(|d| d.as_secs());

    Ok(FileInfo {
        path,
        name,
        extension,
        size_bytes: metadata.len(),
        created,
        modified,
        is_directory: metadata.is_dir(),
    })
}

/// List all assets in the storage directory
#[command]
pub async fn list_storage_assets(storage_path: String) -> Result<Vec<StorageAsset>, String> {
    let path = Path::new(&storage_path);

    if !path.exists() {
        return Err(format!("Storage path not found: {}", storage_path));
    }

    if !path.is_dir() {
        return Err(format!("Storage path is not a directory: {}", storage_path));
    }

    let mut assets = Vec::new();

    for entry in WalkDir::new(path).min_depth(1).max_depth(1) {
        let entry = entry.map_err(|e| format!("Failed to read directory: {}", e))?;

        if entry.file_type().is_dir() {
            let dir_name = entry.file_name().to_string_lossy().to_string();
            let dir_path = entry.path();

            // Check for various model files
            let glb_path = dir_path.join(format!("{}.glb", dir_name));
            let obj_path = dir_path.join(format!("{}.obj", dir_name));
            let fbx_path = dir_path.join(format!("{}.fbx", dir_name));
            let thumbnail_path = dir_path.join("thumbnail.png");

            let has_glb = glb_path.exists();
            let has_obj = obj_path.exists();
            let has_fbx = fbx_path.exists();
            let has_thumbnail = thumbnail_path.exists();

            let glb_size = if has_glb {
                fs::metadata(&glb_path).ok().map(|m| m.len())
            } else {
                None
            };

            assets.push(StorageAsset {
                id: dir_name,
                path: dir_path.to_string_lossy().to_string(),
                has_glb,
                has_obj,
                has_fbx,
                has_thumbnail,
                glb_size,
                thumbnail_path: if has_thumbnail {
                    Some(thumbnail_path.to_string_lossy().to_string())
                } else {
                    None
                },
            });
        }
    }

    Ok(assets)
}

/// Watch a directory for changes
/// Returns the current list of files in the directory
#[command]
pub async fn watch_directory(path: String) -> Result<Vec<FileInfo>, String> {
    let path_obj = Path::new(&path);

    if !path_obj.exists() {
        return Err(format!("Directory not found: {}", path));
    }

    if !path_obj.is_dir() {
        return Err(format!("Path is not a directory: {}", path));
    }

    let mut files = Vec::new();

    for entry in fs::read_dir(path_obj).map_err(|e| format!("Failed to read directory: {}", e))? {
        let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
        let file_path = entry.path();
        let metadata = entry
            .metadata()
            .map_err(|e| format!("Failed to read metadata: {}", e))?;

        let name = file_path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        let extension = file_path
            .extension()
            .map(|e| e.to_string_lossy().to_string());

        let created = metadata
            .created()
            .ok()
            .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
            .map(|d| d.as_secs());

        let modified = metadata
            .modified()
            .ok()
            .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
            .map(|d| d.as_secs());

        files.push(FileInfo {
            path: file_path.to_string_lossy().to_string(),
            name,
            extension,
            size_bytes: metadata.len(),
            created,
            modified,
            is_directory: metadata.is_dir(),
        });
    }

    Ok(files)
}
