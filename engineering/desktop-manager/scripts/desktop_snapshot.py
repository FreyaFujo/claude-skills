#!/usr/bin/env python3
"""
desktop-manager: Desktop Snapshot

Save and restore named window layout snapshots. Captures the HWND, title,
process name, and geometry of every visible window, keyed by snapshot name.

Snapshots are stored as JSON files in ~/.desktop-snapshots/ and restored by
matching saved window titles to currently open windows.

Usage:
    python scripts/desktop_snapshot.py save --name coding
    python scripts/desktop_snapshot.py restore --name coding
    python scripts/desktop_snapshot.py list
    python scripts/desktop_snapshot.py list --json
    python scripts/desktop_snapshot.py delete --name coding
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SNAPSHOT_DIR = Path.home() / ".desktop-snapshots"

# Win32 type definition reused from window_manager pattern
WIN32_TYPE = r"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
        int X, int Y, int cx, int cy, uint uFlags);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int left, top, right, bottom; }
}
"@ -ErrorAction SilentlyContinue
"""

SWP_FLAGS = "0x14"  # SWP_NOZORDER | SWP_NOACTIVATE


def run_ps(script: str) -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1) and result.stderr.strip():
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _sanitize_name(name: str) -> str:
    if not re.match(r"^[\w\-]+$", name):
        raise ValueError(
            f"Snapshot name '{name}': use alphanumeric, hyphen, or underscore only"
        )
    return name


def _snapshot_path(name: str) -> Path:
    return SNAPSHOT_DIR / f"{name}.json"


def capture_windows() -> list[dict]:
    """Return current visible window geometries via PowerShell."""
    ps = (
        WIN32_TYPE
        + r"""
$wins = Get-Process | Where-Object {
    $_.MainWindowHandle -ne [IntPtr]::Zero -and $_.MainWindowTitle -ne ''
} | ForEach-Object {
    $hwnd = $_.MainWindowHandle
    $rect = New-Object WinAPI+RECT
    [void][WinAPI]::GetWindowRect($hwnd, [ref]$rect)
    [PSCustomObject]@{
        hwnd  = $hwnd.ToInt64()
        title = $_.MainWindowTitle
        name  = $_.ProcessName
        pid   = $_.Id
        x     = $rect.left
        y     = $rect.top
        w     = $rect.right  - $rect.left
        h     = $rect.bottom - $rect.top
    }
}
if ($wins) { $wins | ConvertTo-Json -Compress } else { "[]" }
"""
    )
    out = run_ps(ps)
    if not out or out == "[]":
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def set_window_pos(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    ps = WIN32_TYPE + (
        f"[WinAPI]::SetWindowPos([IntPtr]{hwnd}, [IntPtr]::Zero,"
        f" {x}, {y}, {w}, {h}, {SWP_FLAGS})"
    )
    run_ps(ps)


# ── Snapshot operations ──────────────────────────────────────────────────────


def save_snapshot(name: str) -> dict:
    """Capture current window layout and write to ~/.desktop-snapshots/{name}.json."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    windows = capture_windows()
    if not windows:
        raise RuntimeError("No visible windows found to snapshot.")
    payload = {
        "name": name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "count": len(windows),
        "windows": windows,
    }
    _snapshot_path(name).write_text(json.dumps(payload, indent=2))
    return payload


def restore_snapshot(name: str) -> dict:
    """
    Restore a saved layout. Matches saved windows to current windows by title
    (exact match first, then substring). Unmatched entries are skipped.
    """
    path = _snapshot_path(name)
    if not path.exists():
        raise FileNotFoundError(
            f"No snapshot named '{name}'. Run 'list' to see available snapshots."
        )

    saved = json.loads(path.read_text())
    current = capture_windows()

    # Build lookup: title -> hwnd for current windows
    exact: dict[str, int] = {w["title"]: w["hwnd"] for w in current}
    partial: list[dict] = current  # for fallback substring match

    restored, skipped = [], []
    for sw in saved["windows"]:
        hwnd = exact.get(sw["title"])
        if hwnd is None:
            # Fallback: find first current window whose title contains saved title prefix
            match = next(
                (
                    c
                    for c in partial
                    if sw["title"][:30] in c["title"] or c["name"] == sw["name"]
                ),
                None,
            )
            hwnd = match["hwnd"] if match else None

        if hwnd:
            set_window_pos(hwnd, sw["x"], sw["y"], sw["w"], sw["h"])
            restored.append({"title": sw["title"], "hwnd": hwnd})
        else:
            skipped.append(sw["title"])

    return {
        "snapshot": name,
        "restored": len(restored),
        "skipped": len(skipped),
        "details": {"restored": restored, "skipped": skipped},
    }


def list_snapshots() -> list[dict]:
    """Return metadata for all saved snapshots."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for p in sorted(SNAPSHOT_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            snapshots.append(
                {
                    "name": data.get("name", p.stem),
                    "created": data.get("created", "unknown"),
                    "count": data.get("count", 0),
                }
            )
        except (json.JSONDecodeError, KeyError):
            snapshots.append({"name": p.stem, "created": "?", "count": "?"})
    return snapshots


def delete_snapshot(name: str) -> dict:
    path = _snapshot_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No snapshot named '{name}'.")
    path.unlink()
    return {"deleted": name}


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Desktop snapshot — save and restore window layout presets"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_save = sub.add_parser("save", help="Save current window layout")
    p_save.add_argument(
        "--name", required=True, help="Snapshot name (alphanumeric/hyphen)"
    )
    p_save.add_argument("--json", action="store_true")

    p_restore = sub.add_parser("restore", help="Restore a saved layout")
    p_restore.add_argument("--name", required=True)
    p_restore.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="List saved snapshots")
    p_list.add_argument("--json", action="store_true")

    p_delete = sub.add_parser("delete", help="Delete a saved snapshot")
    p_delete.add_argument("--name", required=True)
    p_delete.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(2)

    use_json = getattr(args, "json", False)
    name = _sanitize_name(getattr(args, "name", "")) if hasattr(args, "name") else ""

    try:
        if args.cmd == "save":
            result = save_snapshot(name)
            if use_json:
                print(json.dumps(result, indent=2))
            else:
                print(
                    f"Saved '{name}': {result['count']} windows → {_snapshot_path(name)}"
                )

        elif args.cmd == "restore":
            result = restore_snapshot(name)
            if use_json:
                print(json.dumps(result, indent=2))
            else:
                print(
                    f"Restored '{name}': {result['restored']} windows placed"
                    f", {result['skipped']} skipped"
                )
                if result["details"]["skipped"]:
                    for t in result["details"]["skipped"]:
                        print(f"  skipped: {t[:70]}")

        elif args.cmd == "list":
            snaps = list_snapshots()
            if use_json:
                print(json.dumps(snaps, indent=2))
            else:
                if not snaps:
                    print(f"No snapshots found in {SNAPSHOT_DIR}")
                else:
                    print(f"{'Name':<25} {'Created':<22} Windows")
                    print("─" * 55)
                    for s in snaps:
                        print(f"{s['name']:<25} {s['created']:<22} {s['count']}")

        elif args.cmd == "delete":
            result = delete_snapshot(name)
            if use_json:
                print(json.dumps(result))
            else:
                print(f"Deleted snapshot: {name}")

    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        sys.exit(2)
    except FileNotFoundError as exc:
        if use_json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        if use_json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
