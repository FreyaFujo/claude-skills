#!/usr/bin/env python3
"""
desktop-manager: Process Manager

List running processes, launch applications, and terminate processes on Windows
via PowerShell. Filters to windowed applications by default.

Usage:
    python scripts/process_manager.py list
    python scripts/process_manager.py list --all
    python scripts/process_manager.py list --filter chrome --json
    python scripts/process_manager.py launch --app notepad
    python scripts/process_manager.py launch --path "C:/Windows/System32/notepad.exe"
    python scripts/process_manager.py launch --app code --args "--new-window C:/project"
    python scripts/process_manager.py kill --name notepad
    python scripts/process_manager.py kill --pid 1234
    python scripts/process_manager.py kill --name notepad --json
"""

import argparse
import json
import re
import subprocess
import sys


def run_ps(script: str) -> str:
    """Run a PowerShell script and return stdout. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1) and result.stderr.strip():
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _sanitize_name(name: str) -> str:
    """Allow only safe characters in process names to prevent PS injection."""
    if not re.match(r"^[\w.\-]+$", name):
        raise ValueError(
            f"Invalid process name '{name}': use alphanumeric, dot, or hyphen only"
        )
    return name


def list_processes(filter_name: str = "", all_procs: bool = False) -> list[dict]:
    """
    Return running processes. Without --all, returns only windowed processes.
    Optionally filter by name substring.
    """
    where = ""
    if not all_procs:
        where = "| Where-Object { $_.MainWindowTitle -ne '' }"

    if filter_name:
        safe = _sanitize_name(filter_name)
        where += f" | Where-Object {{ $_.ProcessName -like '*{safe}*' }}"

    ps = f"""
$procs = Get-Process {where} | Select-Object -Property `
    Id, ProcessName, MainWindowTitle,
    @{{n='CpuSec'; e={{[math]::Round($_.CPU, 1)}}}},
    @{{n='MemMB';  e={{[math]::Round($_.WorkingSet64 / 1MB, 1)}}}}
if ($procs) {{ $procs | ConvertTo-Json -Compress }} else {{ "[]" }}
"""
    out = run_ps(ps)
    if not out or out == "[]":
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def launch_app(app: str = "", path: str = "", args: str = "") -> dict:
    """
    Launch an application by name (resolved via PATH / Windows shell) or full path.
    Optional args string is passed as argument list.
    """
    if path:
        target = path.replace("'", "\\'")
        cmd = f"Start-Process '{target}'"
    else:
        safe = _sanitize_name(app)
        cmd = f"Start-Process '{safe}'"

    if args:
        safe_args = args.replace("'", "\\'")
        cmd += f" -ArgumentList '{safe_args}'"

    run_ps(cmd)
    return {"launched": path or app, "args": args}


def kill_process(name: str = "", pid: int = 0) -> dict:
    """
    Terminate one or more processes by name or PID.
    Name supports wildcard (e.g. 'chrome' kills all chrome.exe instances).
    """
    if pid:
        ps = f"Stop-Process -Id {int(pid)} -Force -ErrorAction Stop"
        run_ps(ps)
        return {"killed": {"pid": pid}}
    else:
        safe = _sanitize_name(name)
        ps = f"Stop-Process -Name '{safe}' -Force -ErrorAction Stop"
        run_ps(ps)
        return {"killed": {"name": name}}


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process manager — list, launch, and kill Windows processes"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="List running processes")
    p_list.add_argument(
        "--filter", default="", metavar="NAME", help="Filter by process name substring"
    )
    p_list.add_argument(
        "--all", action="store_true", help="Include background processes (no window)"
    )
    p_list.add_argument("--json", action="store_true")

    p_launch = sub.add_parser("launch", help="Launch an application")
    grp = p_launch.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--app", help="App name (must be in PATH or a known Windows command)"
    )
    grp.add_argument("--path", help="Full path to executable")
    p_launch.add_argument(
        "--args", default="", help="Arguments to pass to the application"
    )
    p_launch.add_argument("--json", action="store_true")

    p_kill = sub.add_parser("kill", help="Terminate a process")
    grp2 = p_kill.add_mutually_exclusive_group(required=True)
    grp2.add_argument("--name", help="Process name (all matching instances)")
    grp2.add_argument("--pid", type=int, help="Process ID")
    p_kill.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(2)

    use_json = getattr(args, "json", False)

    try:
        if args.cmd == "list":
            procs = list_processes(args.filter, getattr(args, "all", False))
            if use_json:
                print(json.dumps(procs, indent=2))
            else:
                print(
                    f"{'PID':<8} {'CPU(s)':<9} {'Mem(MB)':<10} {'Name':<24} Window Title"
                )
                print("─" * 95)
                for p in procs:
                    title = (p.get("MainWindowTitle") or "")[:42]
                    print(
                        f"{p.get('Id', ''):<8} {p.get('CpuSec', ''):<9}"
                        f" {p.get('MemMB', ''):<10} {p.get('ProcessName', '')[:23]:<24} {title}"
                    )
            if not procs:
                print("No matching processes found.")

        elif args.cmd == "launch":
            result = launch_app(args.app or "", args.path or "", args.args)
            if use_json:
                print(json.dumps(result))
            else:
                msg = f"Launched: {result['launched']}"
                if result["args"]:
                    msg += f" {result['args']}"
                print(msg)

        elif args.cmd == "kill":
            result = kill_process(args.name or "", args.pid or 0)
            if use_json:
                print(json.dumps(result))
            else:
                target = args.name or str(args.pid)
                print(f"Killed: {target}")

    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        if use_json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
