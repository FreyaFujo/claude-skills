#!/usr/bin/env python3
"""
desktop-manager: Window Manager

List, move, resize, snap, and tile windows on Windows 10/11 using PowerShell
and Win32 API. Requires PowerShell 5.1+ (default on Windows 10/11).

Usage:
    python scripts/window_manager.py list
    python scripts/window_manager.py list --json
    python scripts/window_manager.py snap --hwnd 1234567 --pos left-half
    python scripts/window_manager.py tile --layout 2col
    python scripts/window_manager.py tile --layout 3col
    python scripts/window_manager.py tile --layout grid4
    python scripts/window_manager.py move --hwnd 1234567 --x 0 --y 0 --w 960 --h 1080
    python scripts/window_manager.py show --hwnd 1234567 --state maximize
    python scripts/window_manager.py show --hwnd 1234567 --state focus
"""

import argparse
import json
import subprocess
import sys

# ── Win32 type definition (loaded once per PS invocation) ───────────────────
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
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int left, top, right, bottom; }
}
"@ -ErrorAction SilentlyContinue
"""

# uFlags: SWP_NOZORDER (0x4) | SWP_NOACTIVATE (0x10) = 0x14
SWP_FLAGS = "0x14"


def run_ps(script: str) -> str:
    """Run PowerShell script and return stdout. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr.strip():
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of primary monitor working area."""
    ps = """
Add-Type -AssemblyName System.Windows.Forms
$s = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
Write-Output "$($s.Width) $($s.Height)"
"""
    out = run_ps(ps)
    w, h = out.split()
    return int(w), int(h)


def list_windows() -> list[dict]:
    """Return visible windows (main window per process) with position and size."""
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
        pid   = $_.Id
        name  = $_.ProcessName
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
    """Move and resize a window without changing its Z-order."""
    ps = (
        WIN32_TYPE
        + f"""
[WinAPI]::SetWindowPos([IntPtr]{hwnd}, [IntPtr]::Zero, {x}, {y}, {w}, {h}, {SWP_FLAGS})
"""
    )
    run_ps(ps)


def show_window(hwnd: int, state: int) -> None:
    """Change window visibility state. SW_MINIMIZE=2, SW_MAXIMIZE=3, SW_RESTORE=9."""
    ps = WIN32_TYPE + f"[WinAPI]::ShowWindow([IntPtr]{hwnd}, {state})"
    run_ps(ps)


def focus_window(hwnd: int) -> None:
    """Bring window to foreground."""
    ps = WIN32_TYPE + f"[WinAPI]::SetForegroundWindow([IntPtr]{hwnd})"
    run_ps(ps)


# ── Layout presets (returns x, y, w, h given screen w, h) ──────────────────
SNAP_POSITIONS: dict[str, callable] = {
    "left-half": lambda sw, sh: (0, 0, sw // 2, sh),
    "right-half": lambda sw, sh: (sw // 2, 0, sw // 2, sh),
    "top-half": lambda sw, sh: (0, 0, sw, sh // 2),
    "bot-half": lambda sw, sh: (0, sh // 2, sw, sh // 2),
    "top-left": lambda sw, sh: (0, 0, sw // 2, sh // 2),
    "top-right": lambda sw, sh: (sw // 2, 0, sw // 2, sh // 2),
    "bot-left": lambda sw, sh: (0, sh // 2, sw // 2, sh // 2),
    "bot-right": lambda sw, sh: (sw // 2, sh // 2, sw // 2, sh // 2),
    "col-1-of-3": lambda sw, sh: (0, 0, sw // 3, sh),
    "col-2-of-3": lambda sw, sh: (sw // 3, 0, sw // 3, sh),
    "col-3-of-3": lambda sw, sh: (sw * 2 // 3, 0, sw // 3, sh),
    "maximize": lambda sw, sh: (0, 0, sw, sh),
}


def tile_windows(layout: str) -> dict:
    """Tile the first N visible windows using a named layout."""
    sw, sh = get_screen_size()
    wins = [w for w in list_windows() if w["w"] > 100 and w["h"] > 100]

    if layout == "2col":
        slots = [
            SNAP_POSITIONS["left-half"](sw, sh),
            SNAP_POSITIONS["right-half"](sw, sh),
        ]
        targets = wins[:2]
    elif layout == "3col":
        slots = [SNAP_POSITIONS[f"col-{i}-of-3"](sw, sh) for i in [1, 2, 3]]
        targets = wins[:3]
    elif layout == "grid4":
        slots = [
            SNAP_POSITIONS["top-left"](sw, sh),
            SNAP_POSITIONS["top-right"](sw, sh),
            SNAP_POSITIONS["bot-left"](sw, sh),
            SNAP_POSITIONS["bot-right"](sw, sh),
        ]
        targets = wins[:4]
    else:
        raise ValueError(f"Unknown layout '{layout}'. Use: 2col, 3col, grid4")

    placed = []
    for win, (x, y, w, h) in zip(targets, slots):
        set_window_pos(win["hwnd"], x, y, w, h)
        placed.append(
            {"hwnd": win["hwnd"], "title": win["title"], "x": x, "y": y, "w": w, "h": h}
        )

    return {"layout": layout, "tiled": len(placed), "windows": placed}


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Window manager — list, snap, tile, and control Windows windows"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="List visible windows")
    p_list.add_argument("--json", action="store_true", help="JSON output")

    p_move = sub.add_parser("move", help="Move and resize a window by HWND")
    p_move.add_argument(
        "--hwnd", type=int, required=True, help="Window handle (from list)"
    )
    p_move.add_argument("--x", type=int, required=True)
    p_move.add_argument("--y", type=int, required=True)
    p_move.add_argument("--w", type=int, required=True)
    p_move.add_argument("--h", type=int, required=True)
    p_move.add_argument("--json", action="store_true")

    p_snap = sub.add_parser("snap", help="Snap a window to a preset screen position")
    p_snap.add_argument("--hwnd", type=int, required=True)
    p_snap.add_argument("--pos", choices=list(SNAP_POSITIONS.keys()), required=True)
    p_snap.add_argument("--json", action="store_true")

    p_tile = sub.add_parser("tile", help="Tile windows in a layout")
    p_tile.add_argument("--layout", choices=["2col", "3col", "grid4"], required=True)
    p_tile.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="Change window state or bring to focus")
    p_show.add_argument("--hwnd", type=int, required=True)
    p_show.add_argument(
        "--state", choices=["minimize", "maximize", "restore", "focus"], required=True
    )
    p_show.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(2)

    use_json = getattr(args, "json", False)

    try:
        if args.cmd == "list":
            wins = list_windows()
            if use_json:
                print(json.dumps(wins, indent=2))
            else:
                print(f"{'HWND':<14} {'PID':<8} {'W×H':<14} {'Name':<20} Title")
                print("─" * 90)
                for w in wins:
                    size = f"{w['w']}×{w['h']}"
                    print(
                        f"{w['hwnd']:<14} {w['pid']:<8} {size:<14}"
                        f" {w['name'][:19]:<20} {w['title'][:45]}"
                    )

        elif args.cmd == "move":
            set_window_pos(args.hwnd, args.x, args.y, args.w, args.h)
            result = {
                "hwnd": args.hwnd,
                "x": args.x,
                "y": args.y,
                "w": args.w,
                "h": args.h,
            }
            if use_json:
                print(json.dumps(result))
            else:
                print(f"Moved {args.hwnd} → ({args.x},{args.y}) {args.w}×{args.h}")

        elif args.cmd == "snap":
            sw, sh = get_screen_size()
            x, y, w, h = SNAP_POSITIONS[args.pos](sw, sh)
            set_window_pos(args.hwnd, x, y, w, h)
            result = {
                "hwnd": args.hwnd,
                "pos": args.pos,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
            if use_json:
                print(json.dumps(result))
            else:
                print(f"Snapped {args.hwnd} to {args.pos}: ({x},{y}) {w}×{h}")

        elif args.cmd == "tile":
            result = tile_windows(args.layout)
            if use_json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Tiled {result['tiled']} windows [{args.layout}]:")
                for w in result["windows"]:
                    print(
                        f"  {w['hwnd']}: ({w['x']},{w['y']}) {w['w']}×{w['h']}  {w['title'][:50]}"
                    )

        elif args.cmd == "show":
            state_map = {"minimize": 2, "maximize": 3, "restore": 9}
            if args.state == "focus":
                focus_window(args.hwnd)
            else:
                show_window(args.hwnd, state_map[args.state])
            result = {"hwnd": args.hwnd, "state": args.state}
            if use_json:
                print(json.dumps(result))
            else:
                print(f"Window {args.hwnd}: {args.state}")

    except Exception as exc:
        if use_json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
