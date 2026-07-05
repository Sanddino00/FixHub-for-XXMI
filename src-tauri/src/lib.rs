use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::Command;

use serde::{Deserialize, Serialize};

const APP_RELEASE_API: &str = "https://api.github.com/repos/Sanddino00/FixHub-for-XXMI/releases/latest";
const RESOURCES_RELEASE_API: &str =
  "https://api.github.com/repos/Sanddino00/Resources-for-Fixmanager-and-Modmanager/releases/latest";
const RESOURCES_ZIP_NAME: &str = "resources_f_m.zip";

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GameInfo {
  name: String,
  key: String,
  subfolder: String,
  mod_folder_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct AppConfig {
  mode: String,
  game_paths: HashMap<String, String>,
  last_updater_release_tag: Option<String>,
  last_app_release_tag: Option<String>,
  last_resources_tag: Option<String>,
}

impl Default for AppConfig {
  fn default() -> Self {
    Self {
      mode: "light".to_string(),
      game_paths: HashMap::new(),
      last_updater_release_tag: None,
      last_app_release_tag: None,
      last_resources_tag: None,
    }
  }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ReleaseAsset {
  name: String,
  browser_download_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ReleaseResponse {
  tag_name: String,
  assets: Vec<ReleaseAsset>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct UpdateCheckResult {
  latest_tag: String,
  update_available: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BootstrapData {
  config: AppConfig,
  games: Vec<GameInfo>,
  resolved_game_paths: HashMap<String, String>,
  app_version: String,
  base_dir: String,
}

fn games() -> Vec<GameInfo> {
  vec![
    GameInfo {
      name: "Genshin Impact".to_string(),
      key: "gi".to_string(),
      subfolder: "gi".to_string(),
      mod_folder_name: "GIMI".to_string(),
    },
    GameInfo {
      name: "Honkai Star Rail".to_string(),
      key: "hsr".to_string(),
      subfolder: "hsr".to_string(),
      mod_folder_name: "SRMI".to_string(),
    },
    GameInfo {
      name: "Wuthering Waves".to_string(),
      key: "wuwa".to_string(),
      subfolder: "wuwa".to_string(),
      mod_folder_name: "WWMI".to_string(),
    },
    GameInfo {
      name: "Zenless Zone Zero".to_string(),
      key: "zzz".to_string(),
      subfolder: "zzz".to_string(),
      mod_folder_name: "ZZMI".to_string(),
    },
    GameInfo {
      name: "Honkai Impact 3rd".to_string(),
      key: "hi3".to_string(),
      subfolder: "hi3".to_string(),
      mod_folder_name: "HIMI".to_string(),
    },
  ]
}

fn find_folder_by_name(root: &Path, wanted_name: &str, max_depth: u8) -> Option<PathBuf> {
  if max_depth == 0 || !root.exists() || !root.is_dir() {
    return None;
  }

  let entries = fs::read_dir(root).ok()?;
  for entry in entries.flatten() {
    let path = entry.path();
    if !path.is_dir() {
      continue;
    }

    let folder_name = path.file_name().map(|x| x.to_string_lossy().to_string())?;
    if folder_name.eq_ignore_ascii_case(wanted_name) {
      return Some(path);
    }

    if let Some(found) = find_folder_by_name(&path, wanted_name, max_depth.saturating_sub(1)) {
      return Some(found);
    }
  }

  None
}

fn discover_default_mod_folder(game: &GameInfo) -> Option<String> {
  let mut roots = vec![];

  if let Some(home) = dirs::home_dir() {
    roots.push(home.clone());
    roots.push(home.join("Desktop"));
    roots.push(home.join("Documents"));
    roots.push(home.join("Downloads"));
    roots.push(home.join("Games"));
    roots.push(home.join("Documents").join("My Games"));
  }

  if let Some(docs) = dirs::document_dir() {
    roots.push(docs.clone());
    roots.push(docs.join("My Games"));
  }

  if let Some(desktop) = dirs::desktop_dir() {
    roots.push(desktop);
  }

  for root in &roots {
    let direct = root.join(&game.mod_folder_name);
    if direct.exists() && direct.is_dir() {
      return Some(direct.to_string_lossy().to_string());
    }
  }

  for root in &roots {
    if let Some(found) = find_folder_by_name(root, &game.mod_folder_name, 3) {
      return Some(found.to_string_lossy().to_string());
    }
  }

  None
}

fn resolve_target_folder(game: &GameInfo, config: &AppConfig) -> Option<String> {
  let override_path = config.game_paths.get(&game.key).cloned().unwrap_or_default();
  let trimmed = override_path.trim().to_string();
  if !trimmed.is_empty() {
    return Some(trimmed);
  }

  discover_default_mod_folder(game)
}

fn resolved_paths_for_ui(config: &AppConfig) -> HashMap<String, String> {
  let mut out = HashMap::new();
  for game in games() {
    if let Some(path) = resolve_target_folder(&game, config) {
      out.insert(game.key.clone(), path);
    }
  }
  out
}

fn base_dir() -> Result<PathBuf, String> {
  let exe = std::env::current_exe().map_err(|e| format!("Failed to resolve current exe: {e}"))?;
  let parent = exe
    .parent()
    .ok_or_else(|| "Failed to resolve executable directory".to_string())?;
  Ok(parent.to_path_buf())
}

fn config_path() -> Result<PathBuf, String> {
  Ok(base_dir()?.join("config.json"))
}

fn resources_dir() -> Result<PathBuf, String> {
  Ok(base_dir()?.join("resources"))
}

fn load_config_sync() -> Result<AppConfig, String> {
  let path = config_path()?;
  if !path.exists() {
    return Ok(AppConfig::default());
  }
  let content = fs::read_to_string(&path)
    .map_err(|e| format!("Failed to read config from {}: {e}", path.display()))?;
  if content.trim().is_empty() {
    return Ok(AppConfig::default());
  }

  let mut config: AppConfig = serde_json::from_str(&content)
    .map_err(|e| format!("Invalid config.json format: {e}"))?;

  if config.mode != "light" && config.mode != "dark" {
    config.mode = "light".to_string();
  }

  Ok(config)
}

fn save_config_sync(config: &AppConfig) -> Result<(), String> {
  let path = config_path()?;
  let serialized = serde_json::to_string_pretty(config).map_err(|e| format!("Failed to serialize config: {e}"))?;
  fs::write(&path, serialized).map_err(|e| format!("Failed to save {}: {e}", path.display()))
}

fn find_game(game_key: &str) -> Option<GameInfo> {
  games().into_iter().find(|g| g.key == game_key)
}

fn fetch_latest_release(api_url: &str) -> Result<ReleaseResponse, String> {
  let client = reqwest::blocking::Client::builder()
    .build()
    .map_err(|e| format!("Failed to build HTTP client: {e}"))?;

  let response = client
    .get(api_url)
    .header("User-Agent", "FixManager-Tauri")
    .send()
    .map_err(|e| format!("Failed to fetch latest release: {e}"))?;

  if !response.status().is_success() {
    return Err(format!("Release API returned HTTP {}", response.status()));
  }

  response
    .json::<ReleaseResponse>()
    .map_err(|e| format!("Failed to parse release response: {e}"))
}

fn compare_versions(v_local: &str, v_online: &str) -> bool {
  let parse = |v: &str| -> Vec<u32> {
    v.split('.')
      .map(|part| part.parse::<u32>().unwrap_or(0))
      .collect::<Vec<u32>>()
  };

  let local = parse(v_local);
  let online = parse(v_online);
  online > local
}

fn parse_version_from_tag(tag: &str) -> Option<String> {
  let trimmed = tag.trim();
  if trimmed.to_lowercase().starts_with("version_") {
    return trimmed.split_once('_').map(|(_, version)| version.to_string());
  }
  if trimmed.starts_with('v') {
    return Some(trimmed.trim_start_matches('v').to_string());
  }
  if trimmed.chars().next().is_some_and(|c| c.is_ascii_digit()) {
    return Some(trimmed.to_string());
  }
  None
}

fn download_file(url: &str, destination: &Path) -> Result<(), String> {
  let client = reqwest::blocking::Client::builder()
    .build()
    .map_err(|e| format!("Failed to build HTTP client: {e}"))?;

  let response = client
    .get(url)
    .header("User-Agent", "FixManager-Tauri")
    .send()
    .map_err(|e| format!("Failed to download asset: {e}"))?;

  if !response.status().is_success() {
    return Err(format!("Asset download failed with HTTP {}", response.status()));
  }

  let bytes = response
    .bytes()
    .map_err(|e| format!("Failed to read downloaded bytes: {e}"))?;

  fs::write(destination, &bytes)
    .map_err(|e| format!("Failed to write {}: {e}", destination.display()))
}

fn replace_file(from: &Path, to: &Path) -> Result<(), String> {
  if to.exists() {
    fs::remove_file(to).map_err(|e| format!("Failed to remove {}: {e}", to.display()))?;
  }
  fs::rename(from, to).map_err(|e| format!("Failed to rename {} to {}: {e}", from.display(), to.display()))
}

fn extract_zip_to_dir(zip_path: &Path, destination_dir: &Path) -> Result<(), String> {
  let zip_file = fs::File::open(zip_path)
    .map_err(|e| format!("Failed to open zip {}: {e}", zip_path.display()))?;

  let mut archive = zip::ZipArchive::new(zip_file).map_err(|e| format!("Invalid zip archive: {e}"))?;

  if destination_dir.exists() {
    fs::remove_dir_all(destination_dir)
      .map_err(|e| format!("Failed to remove existing resources folder: {e}"))?;
  }

  fs::create_dir_all(destination_dir)
    .map_err(|e| format!("Failed to create resources folder {}: {e}", destination_dir.display()))?;

  for i in 0..archive.len() {
    let mut file = archive.by_index(i).map_err(|e| format!("Failed to read zip entry: {e}"))?;
    let outpath = destination_dir.join(file.name());

    if file.name().ends_with('/') {
      fs::create_dir_all(&outpath)
        .map_err(|e| format!("Failed to create directory {}: {e}", outpath.display()))?;
      continue;
    }

    if let Some(parent) = outpath.parent() {
      fs::create_dir_all(parent)
        .map_err(|e| format!("Failed to create directory {}: {e}", parent.display()))?;
    }

    let mut outfile = fs::File::create(&outpath)
      .map_err(|e| format!("Failed to create output file {}: {e}", outpath.display()))?;
    io::copy(&mut file, &mut outfile)
      .map_err(|e| format!("Failed to extract {}: {e}", outpath.display()))?;
  }

  Ok(())
}

#[tauri::command]
fn bootstrap() -> Result<BootstrapData, String> {
  let config = load_config_sync()?;
  let base = base_dir()?;
  let resolved_game_paths = resolved_paths_for_ui(&config);
  Ok(BootstrapData {
    config,
    games: games(),
    resolved_game_paths,
    app_version: env!("CARGO_PKG_VERSION").to_string(),
    base_dir: base.to_string_lossy().to_string(),
  })
}

#[tauri::command]
fn save_config(config: AppConfig) -> Result<(), String> {
  let mut next = config;
  next.game_paths.retain(|_, path| !path.trim().is_empty());
  save_config_sync(&next)
}

#[tauri::command]
fn list_scripts(game_key: String) -> Result<Vec<String>, String> {
  let game = find_game(&game_key).ok_or_else(|| format!("Unknown game key: {game_key}"))?;
  let folder = resources_dir()?.join(game.subfolder);

  if !folder.exists() {
    return Ok(Vec::new());
  }

  let mut scripts = fs::read_dir(&folder)
    .map_err(|e| format!("Failed to read scripts from {}: {e}", folder.display()))?
    .filter_map(Result::ok)
    .filter_map(|entry| {
      let path = entry.path();
      let ext = path.extension()?.to_str()?.to_lowercase();
      if ext == "py" || ext == "exe" {
        return path.file_name().map(|name| name.to_string_lossy().to_string());
      }
      None
    })
    .collect::<Vec<String>>();

  scripts.sort();
  Ok(scripts)
}

#[tauri::command]
fn import_scripts_to_game(game_key: String, file_paths: Vec<String>) -> Result<String, String> {
  let game = find_game(&game_key).ok_or_else(|| format!("Unknown game key: {game_key}"))?;
  if file_paths.is_empty() {
    return Err("No files were provided.".to_string());
  }

  let destination_dir = resources_dir()?.join(&game.subfolder);
  fs::create_dir_all(&destination_dir)
    .map_err(|e| format!("Failed to create destination folder {}: {e}", destination_dir.display()))?;

  let mut imported = 0usize;
  let mut skipped = 0usize;

  for file_path in file_paths {
    let source = PathBuf::from(file_path);
    if !source.exists() || !source.is_file() {
      skipped += 1;
      continue;
    }

    let is_supported = source
      .extension()
      .and_then(|ext| ext.to_str())
      .map(|ext| {
        let lower = ext.to_ascii_lowercase();
        lower == "py" || lower == "exe"
      })
      .unwrap_or(false);

    if !is_supported {
      skipped += 1;
      continue;
    }

    let Some(file_name) = source.file_name() else {
      skipped += 1;
      continue;
    };

    let destination = destination_dir.join(file_name);
    fs::copy(&source, &destination).map_err(|e| {
      format!(
        "Failed to copy {} to {}: {e}",
        source.display(),
        destination.display()
      )
    })?;
    imported += 1;
  }

  if imported == 0 {
    return Err("No valid .py or .exe files were imported.".to_string());
  }

  let skipped_suffix = if skipped > 0 {
    format!(" ({skipped} skipped)")
  } else {
    String::new()
  };

  Ok(format!("Imported {imported} file(s) to {}{}", game.name, skipped_suffix))
}

#[tauri::command]
fn run_script(game_key: String, script_name: String, target_path_override: Option<String>) -> Result<String, String> {
  let game = find_game(&game_key).ok_or_else(|| format!("Unknown game key: {game_key}"))?;
  let config = load_config_sync()?;

  let target_folder = target_path_override
    .map(|s| s.trim().to_string())
    .filter(|s| !s.is_empty())
    .or_else(|| resolve_target_folder(&game, &config))
    .ok_or_else(|| {
      format!(
        "No mod folder found for {}. Select a run path or set a game mod folder in Settings.",
        game.name
      )
    })?;

  let target_path = PathBuf::from(&target_folder);
  if !target_path.exists() {
    return Err(format!("Target folder does not exist: {target_folder}"));
  }

  let source = resources_dir()?.join(game.subfolder).join(&script_name);
  if !source.exists() {
    return Err(format!("Script not found: {}", source.display()));
  }

  let destination = target_path.join(&script_name);
  fs::copy(&source, &destination)
    .map_err(|e| format!("Failed to copy script to target folder: {e}"))?;

  let run_result = (|| -> Result<(), String> {
    let status = if script_name.to_lowercase().ends_with(".py") {
      let embedded_python = base_dir()?.join("python-3.15.0a1-embed-amd64").join("python.exe");
      let python_exec = if embedded_python.exists() {
        embedded_python
      } else {
        PathBuf::from("python")
      };

      Command::new(python_exec)
        .arg(&destination)
        .current_dir(&target_path)
        .status()
        .map_err(|e| format!("Failed to start Python script: {e}"))?
    } else {
      Command::new(&destination)
        .current_dir(&target_path)
        .status()
        .map_err(|e| format!("Failed to start executable: {e}"))?
    };

    if !status.success() {
      return Err(format!("Script exited with code {}", status.code().unwrap_or(-1)));
    }

    Ok(())
  })();

  let _ = fs::remove_file(&destination);
  run_result?;
  Ok(format!("Successfully ran {script_name}"))
}

#[tauri::command]
fn check_app_update() -> Result<UpdateCheckResult, String> {
  let config = load_config_sync()?;
  let release = fetch_latest_release(APP_RELEASE_API)?;
  let online = parse_version_from_tag(&release.tag_name).unwrap_or_else(|| release.tag_name.clone());
  let local = env!("CARGO_PKG_VERSION");
  let release_already_applied = config.last_app_release_tag.as_deref() == Some(release.tag_name.as_str());
  let update_available = if release_already_applied {
    false
  } else {
    compare_versions(local, &online)
  };
  Ok(UpdateCheckResult {
    latest_tag: release.tag_name,
    update_available,
  })
}

#[tauri::command]
fn sync_updater_from_repo(force: Option<bool>) -> Result<String, String> {
  let mut config = load_config_sync()?;
  let release = fetch_latest_release(APP_RELEASE_API)?;
  let tag = release.tag_name.clone();
  let force_redownload = force.unwrap_or(false);

  if !force_redownload && config.last_updater_release_tag.as_deref() == Some(tag.as_str()) {
    return Ok(format!("Updater already synced for {tag}"));
  }

  let updater_asset = release
    .assets
    .iter()
    .find(|asset| asset.name.eq_ignore_ascii_case("update.exe"))
    .ok_or_else(|| "No update.exe asset found in latest app release".to_string())?;

  let dir = base_dir()?;
  let tmp = dir.join("update.exe.new");
  let final_path = dir.join("update.exe");

  download_file(&updater_asset.browser_download_url, &tmp)?;
  replace_file(&tmp, &final_path)?;

  config.last_updater_release_tag = Some(tag.clone());
  save_config_sync(&config)?;
  if force_redownload {
    Ok(format!("Updater re-downloaded from {tag} to {}", final_path.display()))
  } else {
    Ok(format!("Updater synced to {tag} at {}", final_path.display()))
  }
}

#[tauri::command]
fn launch_dedicated_updater() -> Result<String, String> {
  let dir = base_dir()?;
  let updater_path = dir.join("update.exe");
  if !updater_path.exists() {
    return Err("update.exe not found after sync attempt.".to_string());
  }

  #[cfg(target_os = "windows")]
  {
    let script = format!(
      "Start-Process -FilePath '{path}' -WorkingDirectory '{workdir}' -Verb RunAs",
      path = updater_path.to_string_lossy().replace('\\', "\\\\").replace('\'', "''"),
      workdir = dir.to_string_lossy().replace('\\', "\\\\").replace('\'', "''")
    );

    let status = Command::new("powershell")
      .arg("-NoProfile")
      .arg("-ExecutionPolicy")
      .arg("Bypass")
      .arg("-Command")
      .arg(script)
      .status()
      .map_err(|e| format!("Failed to launch updater with elevation: {e}"))?;

    if !status.success() {
      return Err("Updater launch was cancelled or failed at elevation prompt.".to_string());
    }
  }

  #[cfg(not(target_os = "windows"))]
  {
    Command::new(&updater_path)
      .current_dir(&dir)
      .spawn()
      .map_err(|e| format!("Failed to launch updater: {e}"))?;
  }

  Ok("Updater launch requested successfully.".to_string())
}

#[tauri::command]
fn exit_app(app: tauri::AppHandle) {
  app.exit(0);
}

#[tauri::command]
fn check_resources_update() -> Result<UpdateCheckResult, String> {
  let config = load_config_sync()?;
  let release = fetch_latest_release(RESOURCES_RELEASE_API)?;
  let current = config.last_resources_tag.unwrap_or_default();
  Ok(UpdateCheckResult {
    latest_tag: release.tag_name.clone(),
    update_available: release.tag_name != current,
  })
}

#[tauri::command]
fn download_resources() -> Result<String, String> {
  let mut config = load_config_sync()?;
  let release = fetch_latest_release(RESOURCES_RELEASE_API)?;

  let asset = release
    .assets
    .iter()
    .find(|asset| asset.name.eq_ignore_ascii_case(RESOURCES_ZIP_NAME))
    .ok_or_else(|| format!("No {} found in latest resources release", RESOURCES_ZIP_NAME))?;

  let dir = base_dir()?;
  let tmp_zip = dir.join("resources_f_m.tmp.zip");
  download_file(&asset.browser_download_url, &tmp_zip)?;

  let dest = resources_dir()?;
  extract_zip_to_dir(&tmp_zip, &dest)?;
  let _ = fs::remove_file(&tmp_zip);

  config.last_resources_tag = Some(release.tag_name.clone());
  save_config_sync(&config)?;
  Ok(format!("Resources updated to {}", release.tag_name))
}

#[tauri::command]
fn create_desktop_shortcut() -> Result<String, String> {
  #[cfg(not(target_os = "windows"))]
  {
    return Err("Shortcut creation is only supported on Windows.".to_string());
  }

  #[cfg(target_os = "windows")]
  {
    let exe = std::env::current_exe().map_err(|e| format!("Failed to resolve executable: {e}"))?;
    let exe_name = exe
      .file_stem()
      .ok_or_else(|| "Failed to resolve executable name".to_string())?
      .to_string_lossy()
      .to_string();

    let script = format!(
      "$ws = New-Object -ComObject WScript.Shell; $desktop=[Environment]::GetFolderPath('Desktop'); $shortcut=$ws.CreateShortcut((Join-Path $desktop '{exe_name}.lnk')); $shortcut.TargetPath='{target}'; $shortcut.WorkingDirectory='{workdir}'; $shortcut.Save()",
      target = exe.to_string_lossy().replace('\\', "\\\\"),
      workdir = exe
        .parent()
        .ok_or_else(|| "Failed to resolve executable directory".to_string())?
        .to_string_lossy()
        .replace('\\', "\\\\")
    );

    let status = Command::new("powershell")
      .arg("-NoProfile")
      .arg("-ExecutionPolicy")
      .arg("Bypass")
      .arg("-Command")
      .arg(script)
      .status()
      .map_err(|e| format!("Failed to execute shortcut command: {e}"))?;

    if !status.success() {
      return Err("Failed to create desktop shortcut".to_string());
    }

    Ok("Desktop shortcut created successfully".to_string())
  }
}

#[tauri::command]
fn desktop_shortcut_exists() -> Result<bool, String> {
  #[cfg(not(target_os = "windows"))]
  {
    return Ok(false);
  }

  #[cfg(target_os = "windows")]
  {
    let exe = std::env::current_exe().map_err(|e| format!("Failed to resolve executable: {e}"))?;
    let exe_name = exe
      .file_stem()
      .ok_or_else(|| "Failed to resolve executable name".to_string())?
      .to_string_lossy()
      .to_string();
    let desktop_dir = dirs::desktop_dir().ok_or_else(|| "Failed to resolve desktop folder".to_string())?;
    Ok(desktop_dir.join(format!("{exe_name}.lnk")).exists())
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .plugin(tauri_plugin_dialog::init())
    .invoke_handler(tauri::generate_handler![
      bootstrap,
      save_config,
      list_scripts,
      import_scripts_to_game,
      run_script,
      check_app_update,
      sync_updater_from_repo,
      launch_dedicated_updater,
      exit_app,
      check_resources_update,
      download_resources,
      create_desktop_shortcut,
      desktop_shortcut_exists
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
