import { useEffect, useMemo, useState } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'
import { getCurrentWindow } from '@tauri-apps/api/window'
import './App.css'

type GameInfo = {
  name: string
  key: string
  subfolder: string
  mod_folder_name: string
}

type AppConfig = {
  mode: 'light' | 'dark'
  game_paths: Record<string, string>
  last_updater_release_tag: string | null
  last_app_release_tag: string | null
  last_resources_tag: string | null
}

type BootstrapData = {
  config: AppConfig
  games: GameInfo[]
  resolved_game_paths: Record<string, string>
  base_dir: string
}

type UpdateCheckResult = {
  latest_tag: string
  update_available: boolean
}

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [games, setGames] = useState<GameInfo[]>([])
  const [selectedGame, setSelectedGame] = useState('')
  const [scripts, setScripts] = useState<string[]>([])
  const [selectedScript, setSelectedScript] = useState('')
  const [status, setStatus] = useState('Loading...')
  const [baseDir, setBaseDir] = useState('')
  const [appUpdate, setAppUpdate] = useState<UpdateCheckResult | null>(null)
  const [resourcesUpdate, setResourcesUpdate] = useState<UpdateCheckResult | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [startupError, setStartupError] = useState('')
  const [activePage, setActivePage] = useState<'launcher' | 'settings' | 'updates'>('launcher')
  const [resolvedGamePaths, setResolvedGamePaths] = useState<Record<string, string>>({})
  const [runPathOverrides, setRunPathOverrides] = useState<Record<string, string>>({})
  const [isDragOver, setIsDragOver] = useState(false)
  const [updatesStatus, setUpdatesStatus] = useState('')

  const activeTargetPath = useMemo(() => {
    if (!selectedGame) {
      return ''
    }
    return runPathOverrides[selectedGame] || config?.game_paths[selectedGame] || resolvedGamePaths[selectedGame] || ''
  }, [config, selectedGame, resolvedGamePaths, runPathOverrides])

  const updatesAvailable = Boolean(appUpdate?.update_available || resourcesUpdate?.update_available)

  useEffect(() => {
    const initialize = async () => {
      try {
        const data = await invoke<BootstrapData>('bootstrap')
        setConfig(data.config)
        setGames(data.games)
        setResolvedGamePaths(data.resolved_game_paths)
        setBaseDir(data.base_dir)

        const firstGame = data.games[0]?.key || ''
        setSelectedGame(firstGame)

        applyTheme(data.config.mode)
        setStatus('Ready')

        await Promise.all([refreshAppUpdate(), refreshResourcesUpdate()])
      } catch (error) {
        const message = String(error)
        setStatus(message)
        setStartupError(message)
      }
    }

    void initialize()
  }, [])

  useEffect(() => {
    const loadScripts = async () => {
      if (!selectedGame) {
        return
      }
      try {
        const nextScripts = await invoke<string[]>('list_scripts', { gameKey: selectedGame })
        setScripts(nextScripts)
        setSelectedScript(nextScripts[0] || '')
      } catch (error) {
        setStatus(String(error))
      }
    }

    void loadScripts()
  }, [selectedGame])

  useEffect(() => {
    let dispose: (() => void) | undefined

    const listenForDrops = async () => {
      const unlisten = await getCurrentWindow().onDragDropEvent(async (event) => {
        if (event.payload.type === 'enter' || event.payload.type === 'over') {
          setIsDragOver(true)
          return
        }

        if (event.payload.type === 'leave') {
          setIsDragOver(false)
          return
        }

        if (event.payload.type !== 'drop') {
          return
        }

        setIsDragOver(false)

        if (!selectedGame) {
          setStatus('Select a game before dropping files.')
          return
        }

        const filePaths = event.payload.paths.filter((path) => /\.(py|exe)$/i.test(path))
        if (filePaths.length === 0) {
          setStatus('Only .py and .exe files can be imported.')
          return
        }

        setIsBusy(true)
        try {
          const result = await invoke<string>('import_scripts_to_game', {
            gameKey: selectedGame,
            filePaths,
          })
          setStatus(result)

          const nextScripts = await invoke<string[]>('list_scripts', { gameKey: selectedGame })
          setScripts(nextScripts)
          setSelectedScript(nextScripts[0] || '')
        } catch (error) {
          setStatus(String(error))
        } finally {
          setIsBusy(false)
        }
      })

      dispose = unlisten
    }

    void listenForDrops()

    return () => {
      dispose?.()
    }
  }, [selectedGame])

  const applyTheme = (mode: 'light' | 'dark') => {
    document.documentElement.setAttribute('data-theme', mode)
  }

  const refreshAppUpdate = async () => {
    setUpdatesStatus('Checking app updates...')
    try {
      const res = await invoke<UpdateCheckResult>('check_app_update')
      setAppUpdate(res)
      setUpdatesStatus(
        res.update_available
          ? `App update available: ${res.latest_tag}`
          : `App is up to date (${res.latest_tag})`,
      )
    } catch (error) {
      setAppUpdate(null)
      setUpdatesStatus(`Could not check app updates right now: ${String(error)}`)
    }
  }

  const refreshResourcesUpdate = async () => {
    setUpdatesStatus('Checking resources updates...')
    try {
      const res = await invoke<UpdateCheckResult>('check_resources_update')
      setResourcesUpdate(res)
      setUpdatesStatus(
        res.update_available
          ? `Resources update available: ${res.latest_tag}`
          : `Resources are up to date (${res.latest_tag})`,
      )
    } catch (error) {
      setResourcesUpdate(null)
      setUpdatesStatus(`Could not check resources updates right now: ${String(error)}`)
    }
  }

  const pickFolder = async (defaultPath?: string): Promise<string | null> => {
    const selected = await open({
      directory: true,
      multiple: false,
      title: 'Select folder',
      ...(defaultPath ? { defaultPath } : {}),
    })

    if (Array.isArray(selected)) {
      return selected[0] ?? null
    }
    return selected
  }

  const updateConfig = (updater: (prev: AppConfig) => AppConfig) => {
    setConfig((prev) => (prev ? updater(prev) : prev))
  }

  const saveSettings = async () => {
    if (!config) {
      return
    }
    setIsBusy(true)
    try {
      await invoke('save_config', { config })
      const data = await invoke<BootstrapData>('bootstrap')
      setResolvedGamePaths(data.resolved_game_paths)
      setStatus('Settings saved')
    } catch (error) {
      setStatus(String(error))
    } finally {
      setIsBusy(false)
    }
  }

  const runSelectedScript = async () => {
    if (!selectedScript || !selectedGame) {
      return
    }
    setIsBusy(true)
    setStatus(`Running ${selectedScript}...`)
    try {
      const res = await invoke<string>('run_script', {
        gameKey: selectedGame,
        scriptName: selectedScript,
        targetPathOverride: runPathOverrides[selectedGame] || null,
      })
      setStatus(res)
    } catch (error) {
      setStatus(String(error))
    } finally {
      setIsBusy(false)
    }
  }

  const runUpdater = async () => {
    setIsBusy(true)
    try {
      setUpdatesStatus('Preparing updater...')
      await invoke<string>('sync_updater_from_repo', { force: true })
      const msg = await invoke<string>('launch_dedicated_updater')
      setStatus(msg)
      setUpdatesStatus('Updater launched. Closing app...')
      await invoke('exit_app')
    } catch (error) {
      setStatus(String(error))
      setUpdatesStatus(`Update failed: ${String(error)}`)
    } finally {
      setIsBusy(false)
    }
  }

  const downloadResources = async () => {
    setIsBusy(true)
    try {
      const msg = await invoke<string>('download_resources')
      setStatus(msg)
      setUpdatesStatus(msg)
      await refreshResourcesUpdate()
      const nextScripts = await invoke<string[]>('list_scripts', { gameKey: selectedGame })
      setScripts(nextScripts)
      setSelectedScript(nextScripts[0] || '')
    } catch (error) {
      setStatus(String(error))
    } finally {
      setIsBusy(false)
    }
  }

  const createShortcut = async () => {
    setIsBusy(true)
    try {
      const msg = await invoke<string>('create_desktop_shortcut')
      setStatus(msg)
    } catch (error) {
      setStatus(String(error))
    } finally {
      setIsBusy(false)
    }
  }

  if (!config) {
    return (
      <main className="shell">
        <section className="card">
          <h2>Loading FixManager...</h2>
          {startupError && (
            <p className="muted">
              Startup error: {startupError}
            </p>
          )}
        </section>
      </main>
    )
  }

  return (
    <main className="shell">
      {isDragOver && (
        <div className="drop-overlay">
          Drop .py or .exe files to import into the selected game fixes
        </div>
      )}

      <header className="topbar">
        <h1>FixManager</h1>
        <div className="toolbar">
          <button
            type="button"
            className={activePage === 'launcher' ? 'icon-btn active' : 'icon-btn'}
            onClick={() => setActivePage('launcher')}
            title="Launcher"
          >
            ⌂
          </button>
          <button
            type="button"
            className={activePage === 'settings' ? 'icon-btn active' : 'icon-btn'}
            onClick={() => setActivePage('settings')}
            title="Settings"
          >
            ⚙
          </button>
          <button
            type="button"
            className={activePage === 'updates' ? 'icon-btn active notify' : 'icon-btn notify'}
            onClick={() => setActivePage('updates')}
            title="Updates"
          >
            ⟳
            {updatesAvailable && <span className="notif-dot" aria-hidden="true" />}
          </button>
        </div>
      </header>

      {activePage === 'launcher' && (
        <section className="panel grid-main">
          <article className="card">
            <h2>Launcher</h2>
            <p className="muted">Drag and drop .py/.exe files anywhere in this window to import fixes.</p>
            <div>
              <p className="muted">Game</p>
              <div className="game-buttons">
                {games.map((game) => (
                  <button
                    key={game.key}
                    type="button"
                    className={selectedGame === game.key ? 'game-btn active' : 'game-btn ghost'}
                    onClick={() => setSelectedGame(game.key)}
                  >
                    {game.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="target-line">
              <span>Run path:</span>
              <strong>{activeTargetPath || 'Not configured'}</strong>
            </div>

            <div className="button-row">
              <button
                type="button"
                className="ghost"
                disabled={!selectedGame || isBusy}
                onClick={async () => {
                  const folder = await pickFolder(activeTargetPath || resolvedGamePaths[selectedGame] || undefined)
                  if (!folder || !selectedGame) {
                    return
                  }
                  setRunPathOverrides((prev) => ({
                    ...prev,
                    [selectedGame]: folder,
                  }))
                }}
              >
                Choose Run Path
              </button>
              <button
                type="button"
                className="ghost"
                disabled={!selectedGame || isBusy || !runPathOverrides[selectedGame]}
                onClick={() => {
                  if (!selectedGame) {
                    return
                  }
                  setRunPathOverrides((prev) => {
                    const next = { ...prev }
                    delete next[selectedGame]
                    return next
                  })
                }}
              >
                Use Game Mod Folder
              </button>
            </div>

            <div>
              <p className="muted">Fixes</p>
              <ul className="fix-list">
                {scripts.length === 0 && <li className="fix-item empty">No fixes found</li>}
                {scripts.map((script) => (
                  <li key={script}>
                    <button
                      type="button"
                      className={selectedScript === script ? 'fix-item active' : 'fix-item ghost'}
                      onClick={() => setSelectedScript(script)}
                    >
                      {script}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div className="button-row">
              <button
                type="button"
                disabled={isBusy || !selectedScript || !activeTargetPath}
                onClick={runSelectedScript}
              >
                Run Script
              </button>
              <button
                type="button"
                className="ghost"
                disabled={isBusy}
                onClick={async () => {
                  const nextScripts = await invoke<string[]>('list_scripts', { gameKey: selectedGame })
                  setScripts(nextScripts)
                  setSelectedScript(nextScripts[0] || '')
                }}
              >
                Refresh
              </button>
            </div>
          </article>

          <article className="card status-card">
            <h2>Status</h2>
            <p>{status}</p>
            <div className="badge-stack">
              <span className={appUpdate ? (appUpdate.update_available ? 'badge warn' : 'badge ok') : 'badge info'}>
                App: {appUpdate ? (appUpdate.update_available ? `Update ${appUpdate.latest_tag}` : 'Up to date') : 'Unknown'}
              </span>
              <span className={resourcesUpdate ? (resourcesUpdate.update_available ? 'badge warn' : 'badge ok') : 'badge info'}>
                Resources:{' '}
                {resourcesUpdate ? (resourcesUpdate.update_available ? `Update ${resourcesUpdate.latest_tag}` : 'Up to date') : 'Unknown'}
              </span>
            </div>
            <p className="muted">Base folder: {baseDir}</p>
          </article>
        </section>
      )}

      {activePage === 'settings' && (
        <section className="panel">
          <article className="card">
            <h2>Settings</h2>

            <div className="field-inline">
              <label>Theme</label>
              <button
                type="button"
                className="ghost"
                onClick={() => {
                  const nextMode = config.mode === 'dark' ? 'light' : 'dark'
                  applyTheme(nextMode)
                  updateConfig((prev) => ({ ...prev, mode: nextMode }))
                }}
              >
                Toggle {config.mode === 'dark' ? 'Light' : 'Dark'}
              </button>
            </div>

            <div className="divider" />

            {games.map((game) => (
              <label key={game.key}>
                {game.name} mod folder
                <div className="path-row">
                  <input
                    value={config.game_paths[game.key] ?? ''}
                    onChange={(e) =>
                      updateConfig((prev) => ({
                        ...prev,
                        game_paths: {
                          ...prev.game_paths,
                          [game.key]: e.target.value,
                        },
                      }))
                    }
                      placeholder={`Default mod folder: ${resolvedGamePaths[game.key] || game.mod_folder_name}`}
                  />
                  <button
                    type="button"
                    className="ghost"
                    onClick={async () => {
                      const folder = await pickFolder(resolvedGamePaths[game.key] || undefined)
                      if (!folder) {
                        return
                      }
                      updateConfig((prev) => ({
                        ...prev,
                        game_paths: {
                          ...prev.game_paths,
                          [game.key]: folder,
                        },
                      }))
                    }}
                  >
                    Browse
                  </button>
                </div>
              </label>
            ))}

            <div className="divider" />

            <h3>Shortcut</h3>
            <p className="muted">Create a desktop shortcut manually if you need one.</p>
            <button type="button" className="ghost" disabled={isBusy} onClick={createShortcut}>
              Create Desktop Shortcut
            </button>

            <button type="button" disabled={isBusy} onClick={saveSettings}>
              Save Settings
            </button>
          </article>
        </section>
      )}

      {activePage === 'updates' && (
        <section className="panel">
          <article className="card">
            <h2>Updates and Resources</h2>

            <p className="muted">{updatesStatus || 'Use Update App to sync updater + run update.exe automatically.'}</p>

            <div className="badge-stack">
              <span className={appUpdate?.update_available ? 'badge warn' : 'badge ok'}>
                App: {appUpdate?.update_available ? `Update ${appUpdate.latest_tag}` : 'Up to date'}
              </span>
              <span className={resourcesUpdate?.update_available ? 'badge warn' : 'badge ok'}>
                Resources:{' '}
                {resourcesUpdate?.update_available ? `Update ${resourcesUpdate.latest_tag}` : 'Up to date'}
              </span>
            </div>

            <div className="button-row">
              <button type="button" disabled={isBusy} onClick={runUpdater}>
                Update App
              </button>
            </div>

            <div className="divider" />

            <p className="muted">
              Resource package source: Resources-for-Fixmanager-and-Modmanager / resources_f_m.zip
            </p>

            <div className="button-row">
              <button
                type="button"
                className="ghost"
                disabled={isBusy}
                onClick={refreshResourcesUpdate}
              >
                Check Resources
              </button>
              <button type="button" disabled={isBusy} onClick={downloadResources}>
                Download Resources (Optional)
              </button>
            </div>
          </article>
        </section>
      )}
    </main>
  )
}

export default App
