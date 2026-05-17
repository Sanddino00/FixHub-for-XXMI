use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::thread;
use std::time::Duration;

use serde::{Deserialize, Serialize};

const APP_RELEASE_API: &str = "https://api.github.com/repos/Sanddino00/FixHub-for-XXMI/releases/latest";
const TARGET_APP_EXE: &str = "fixmanager.exe";

#[derive(Debug, Deserialize)]
struct ReleaseAsset {
    name: String,
    browser_download_url: String,
}

#[derive(Debug, Deserialize)]
struct ReleaseResponse {
    tag_name: String,
    assets: Vec<ReleaseAsset>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct AppConfig {
    mode: String,
    game_paths: std::collections::HashMap<String, String>,
    last_updater_release_tag: Option<String>,
    last_app_release_tag: Option<String>,
    last_resources_tag: Option<String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            mode: "light".to_string(),
            game_paths: std::collections::HashMap::new(),
            last_updater_release_tag: None,
            last_app_release_tag: None,
            last_resources_tag: None,
        }
    }
}

fn log_line(message: &str) {
    println!("[update.exe] {message}");
}

fn fetch_latest_release() -> Result<ReleaseResponse, String> {
    let client = reqwest::blocking::Client::builder()
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {e}"))?;

    let response = client
        .get(APP_RELEASE_API)
        .header("User-Agent", "FixManager-Updater")
        .send()
        .map_err(|e| format!("Failed to query release API: {e}"))?;

    if !response.status().is_success() {
        return Err(format!("Release API returned HTTP {}", response.status()));
    }

    response
        .json::<ReleaseResponse>()
        .map_err(|e| format!("Failed to parse release response: {e}"))
}

fn download_to_path(url: &str, destination: &Path) -> Result<(), String> {
    let client = reqwest::blocking::Client::builder()
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {e}"))?;

    let response = client
        .get(url)
        .header("User-Agent", "FixManager-Updater")
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

fn wait_for_unlock(target: &Path) {
    for _ in 0..60 {
        if !target.exists() {
            return;
        }

        let test_path = target.with_extension("unlock-test");
        let renamed = fs::rename(target, &test_path)
            .and_then(|_| fs::rename(&test_path, target))
            .is_ok();

        if renamed {
            return;
        }

        thread::sleep(Duration::from_millis(500));
    }
}

fn replace_target(new_file: &Path, target_file: &Path) -> Result<(), String> {
    if target_file.exists() {
        wait_for_unlock(target_file);
        if target_file.exists() {
            fs::remove_file(target_file)
                .map_err(|e| format!("Failed to remove {}: {e}", target_file.display()))?;
        }
    }

    fs::rename(new_file, target_file).map_err(|e| {
        format!(
            "Failed to move {} to {}: {e}",
            new_file.display(),
            target_file.display()
        )
    })
}

fn launch_updated_app(path: &Path) -> Result<(), String> {
    Command::new(path)
        .spawn()
        .map_err(|e| format!("Failed to launch updated app: {e}"))?;
    Ok(())
}

fn updater_dir() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| format!("Failed to resolve updater path: {e}"))?;
    exe.parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "Failed to resolve updater directory".to_string())
}

fn config_path(dir: &Path) -> PathBuf {
    dir.join("config.json")
}

fn load_config_sync(dir: &Path) -> Result<AppConfig, String> {
    let path = config_path(dir);
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

fn save_config_sync(dir: &Path, config: &AppConfig) -> Result<(), String> {
    let path = config_path(dir);
    let serialized = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config: {e}"))?;
    fs::write(&path, serialized).map_err(|e| format!("Failed to save {}: {e}", path.display()))
}

fn run() -> Result<(), String> {
    let dir = updater_dir()?;
    let target_path = dir.join(TARGET_APP_EXE);

    log_line("Checking latest app release...");
    let release = fetch_latest_release()?;

    let app_asset = release
        .assets
        .iter()
        .find(|a| a.name.eq_ignore_ascii_case(TARGET_APP_EXE))
        .or_else(|| {
            release
                .assets
                .iter()
                .find(|a| a.name.to_ascii_lowercase().ends_with(".exe") && !a.name.eq_ignore_ascii_case("update.exe"))
        })
        .ok_or_else(|| "No app .exe asset found in latest release".to_string())?;

    let tmp_path = dir.join(format!("{}.new", TARGET_APP_EXE));
    log_line(&format!("Downloading {} ({})", app_asset.name, release.tag_name));
    download_to_path(&app_asset.browser_download_url, &tmp_path)?;

    log_line("Replacing app executable...");
    replace_target(&tmp_path, &target_path)?;

    let mut config = load_config_sync(&dir)?;
    config.last_app_release_tag = Some(release.tag_name.clone());
    save_config_sync(&dir, &config)?;

    log_line("Launching updated app...");
    launch_updated_app(&target_path)?;

    Ok(())
}

fn main() {
    if let Err(err) = run() {
        eprintln!("[update.exe] {err}");
    }
}
