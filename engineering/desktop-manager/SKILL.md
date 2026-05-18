---
name: "desktop-manager"
description: "Windows desktop automation skill for Claude Code. Manages windows, processes, and layouts via PowerShell and Win32 API. Use when: user wants to tile or snap windows, arrange apps side by side, launch or kill processes, list what's open, save a desktop layout, or restore a named workspace. Trigger phrases: 'tile my windows', 'snap VS Code to the left', 'launch notepad', 'kill Chrome', 'list open windows', 'save my coding layout', 'restore my layout', 'arrange windows 2-column', 'what's running', 'close all instances of X'."
license: MIT
metadata:
  version: 1.0.0
  author: VSD Communications
  category: engineering
  updated: 2026-05-19
  platform: windows
---

# Desktop Manager

> Tile. Snap. Launch. Restore. Full Windows desktop control from Claude Code.

PowerShell + Win32 API automation for Windows 10/11. No third-party tools. No admin rights required for standard window operations.

---

## Slash Commands

| Command | What it does |
|---------|-------------|
| `/desktop:windows` | List all open windows with HWND, PID, and geometry |
| `/desktop:tile` | Tile foreground windows in 2-column, 3-column, or 2×2 grid |
| `/desktop:snap` | Snap a specific window to a screen position |
| `/desktop:processes` | List, launch, or kill processes |
| `/desktop:snapshot` | Save or restore a named window layout |

---

## When This Skill Activates

Recognize these patterns:

- "Tile my windows" / "arrange side by side" / "split screen"
- "Snap [app] to the left / right / corner"
- "Launch [app]" / "open [app]" / "start [app]"
- "Kill [process]" / "close all [app] windows"
- "What's running?" / "list open windows"
- "Save my layout as [name]" / "restore [name] layout"
- Any request involving window positions, screen arrangements, or process control

---

## Workflow

### `/desktop:windows` — List & Inspect Windows

1. Run the window lister to get current state:
   ```bash
   python scripts/window_manager.py list
   ```
2. Output shows: HWND (handle), PID, W×H dimensions, process name, window title.
3. Use HWND values from this output for `snap`, `move`, and `show` commands.
4. To get JSON for further processing:
   ```bash
   python scripts/window_manager.py list --json
   ```

### `/desktop:tile` — Tile Windows

Identify which layout the user wants, then apply it. Tiling acts on the first N visible
windows in the order returned by `list`.

```bash
# Side-by-side (first 2 windows)
python scripts/window_manager.py tile --layout 2col

# Three columns (first 3 windows)
python scripts/window_manager.py tile --layout 3col

# 2×2 grid (first 4 windows)
python scripts/window_manager.py tile --layout grid4
```

If the user wants a specific app in a specific position, use `snap` instead.

### `/desktop:snap` — Snap a Single Window

1. Run `list` to get the HWND for the target window.
2. Apply snap position:
   ```bash
   python scripts/window_manager.py snap --hwnd <HWND> --pos left-half
   python scripts/window_manager.py snap --hwnd <HWND> --pos top-right
   ```
3. For exact pixel control:
   ```bash
   python scripts/window_manager.py move --hwnd <HWND> --x 0 --y 0 --w 960 --h 1080
   ```
4. To change window state:
   ```bash
   python scripts/window_manager.py show --hwnd <HWND> --state maximize
   python scripts/window_manager.py show --hwnd <HWND> --state minimize
   python scripts/window_manager.py show --hwnd <HWND> --state focus
   ```

**Available snap positions:** `left-half`, `right-half`, `top-half`, `bot-half`,
`top-left`, `top-right`, `bot-left`, `bot-right`, `col-1-of-3`, `col-2-of-3`,
`col-3-of-3`, `maximize`

### `/desktop:processes` — Process Management

**List windowed processes (default):**
```bash
python scripts/process_manager.py list
python scripts/process_manager.py list --filter chrome
python scripts/process_manager.py list --all          # include background processes
```

**Launch an application:**
```bash
python scripts/process_manager.py launch --app notepad
python scripts/process_manager.py launch --app code --args "--new-window"
python scripts/process_manager.py launch --path "C:/Program Files/app/app.exe"
```

**Terminate a process:**
```bash
python scripts/process_manager.py kill --name chrome    # kills all chrome.exe
python scripts/process_manager.py kill --pid 12345
```

### `/desktop:snapshot` — Save & Restore Layouts

Save the current window layout before switching contexts:
```bash
python scripts/desktop_snapshot.py save --name coding
python scripts/desktop_snapshot.py save --name meetings
```

Restore when returning to a context:
```bash
python scripts/desktop_snapshot.py restore --name coding
```

List and manage snapshots:
```bash
python scripts/desktop_snapshot.py list
python scripts/desktop_snapshot.py delete --name old-layout
```

Snapshots are stored as JSON in `~/.desktop-snapshots/`. Restore matches windows
by title (exact, then prefix), then by process name as fallback.

---

## Tooling

### `scripts/window_manager.py`

Controls window positions, sizes, states, and layout presets via Win32 API.

| Subcommand | Purpose |
|-----------|---------|
| `list` | Enumerate visible windows with HWND and geometry |
| `move` | Set exact x, y, width, height for a window |
| `snap` | Snap to a named position (left-half, top-right, etc.) |
| `tile` | Tile first N windows: 2col, 3col, grid4 |
| `show` | Minimize, maximize, restore, or focus a window |

All subcommands support `--json` for structured output.

### `scripts/process_manager.py`

Lists, launches, and terminates Windows processes.

| Subcommand | Purpose |
|-----------|---------|
| `list` | Windowed processes by default; `--all` for background; `--filter NAME` to search |
| `launch` | Start an app by name (`--app`) or full path (`--path`); optional `--args` |
| `kill` | Stop by `--name` (all matching) or `--pid` |

Process names are sanitized to prevent PowerShell injection.

### `scripts/desktop_snapshot.py`

Saves and restores full window layout snapshots as named JSON files in `~/.desktop-snapshots/`.

| Subcommand | Purpose |
|-----------|---------|
| `save --name X` | Capture current layout |
| `restore --name X` | Re-apply saved positions (matches by title, then process name) |
| `list` | Show all saved snapshots with creation date and window count |
| `delete --name X` | Remove a snapshot |

---

## Snap Position Quick Reference

| Position | Description |
|----------|-------------|
| `left-half` | Left 50% of screen |
| `right-half` | Right 50% of screen |
| `top-half` / `bot-half` | Top or bottom 50% |
| `top-left` / `top-right` | Top quadrant |
| `bot-left` / `bot-right` | Bottom quadrant |
| `col-1-of-3` / `col-2-of-3` / `col-3-of-3` | Three equal columns |
| `maximize` | Full working area |

Screen dimensions are read from `System.Windows.Forms.Screen.PrimaryScreen.WorkingArea`
(excludes taskbar). All measurements are in pixels.

---

## Proactive Triggers

Flag these without being asked:

- **Multiple windows open** when user mentions switching context → suggest saving a snapshot first.
- **User references "left / right side"** for windows → `snap` is the right tool, not `tile`.
- **User wants to "reopen my setup"** → check if a matching snapshot exists with `list`.
- **User asks "what PID is X"** → `process_manager.py list --filter X` gives both PID and HWND.
- **Tile produces wrong results** → remind user that `tile` uses window order from `list`; run `list` first to confirm ordering.

---

## Requirements

- Windows 10 or Windows 11
- PowerShell 5.1+ (default on both; no install needed)
- Python 3.9+ (standard library only — no pip install required)
- No admin rights required for window positioning and process listing

---

## Additional Resources

### Reference Files

- **`references/powershell-window-api.md`** — Win32 API functions used, `Add-Type` patterns,
  and how to extend scripts with additional Win32 calls (full-screen enumeration, multi-monitor,
  DPI awareness, virtual desktops)

---

## Related Skills

- **browser-automation** — Automate browser-specific interactions beyond window positioning.
- **env-secrets-manager** — Manage environment variables set before launching apps.
- **git-worktree-manager** — Pairs well: open each worktree in a snapped window.
- **docker-development** — Launch and monitor Docker Desktop alongside dev windows.
