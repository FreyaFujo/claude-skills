# PowerShell Window API Reference

Reference for the Win32 API functions used in desktop-manager scripts and how to extend
them for advanced use cases.

---

## Core Pattern: `Add-Type` for Win32

PowerShell has no native window management cmdlets. All window control goes through
`Add-Type` to compile and expose C# P/Invoke signatures at runtime:

```powershell
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int left, top, right, bottom; }
}
"@ -ErrorAction SilentlyContinue  # SilentlyContinue skips error if type already loaded
```

Use `-ErrorAction SilentlyContinue` on every `Add-Type` call — if the type was already
compiled in the same PS session it will throw; this suppresses that error harmlessly.

---

## Win32 Functions Used

### GetWindowRect

```csharp
[DllImport("user32.dll")]
public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
```

Returns the bounding rectangle of the window **including borders and title bar** in
screen coordinates. For borderless/maximized windows, `left` and `top` may be negative
(Windows 10+ extends invisible borders off-screen for shadow rendering).

**Usage:**
```powershell
$rect = New-Object WinAPI+RECT
[WinAPI]::GetWindowRect($hwnd, [ref]$rect)
$width  = $rect.right  - $rect.left
$height = $rect.bottom - $rect.top
```

---

### SetWindowPos

```csharp
[DllImport("user32.dll")]
public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
    int X, int Y, int cx, int cy, uint uFlags);
```

Moves and/or resizes a window. The scripts use `uFlags = 0x14`:
- `0x0004` — `SWP_NOZORDER`: keep current Z-order (don't bring to front)
- `0x0010` — `SWP_NOACTIVATE`: don't steal focus

**Common flag combinations:**

| uFlags | Effect |
|--------|--------|
| `0x0014` | Move/resize without changing Z-order or focus (recommended) |
| `0x0001` | `SWP_NOSIZE` — move only, keep current size |
| `0x0002` | `SWP_NOMOVE` — resize only, keep current position |
| `0x0040` | `SWP_SHOWWINDOW` — make visible if hidden |

**hWndInsertAfter special values:**

| Value | Meaning |
|-------|---------|
| `[IntPtr]::Zero` | No Z-order change |
| `[IntPtr](-1)` | `HWND_TOPMOST` — always on top |
| `[IntPtr](-2)` | `HWND_NOTOPMOST` — remove always-on-top |

---

### ShowWindow

```csharp
[DllImport("user32.dll")]
public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
```

**nCmdShow values:**

| Value | Constant | Effect |
|-------|----------|--------|
| `0` | `SW_HIDE` | Hide window |
| `1` | `SW_SHOWNORMAL` | Show/restore normal |
| `2` | `SW_MINIMIZE` | Minimize to taskbar |
| `3` | `SW_MAXIMIZE` | Maximize |
| `5` | `SW_SHOW` | Show at current size/position |
| `6` | `SW_MINIMIZE` (alt) | Minimize without activating |
| `9` | `SW_RESTORE` | Restore from min/max |

---

### SetForegroundWindow / GetForegroundWindow

```csharp
[DllImport("user32.dll")]
public static extern bool SetForegroundWindow(IntPtr hWnd);

[DllImport("user32.dll")]
public static extern IntPtr GetForegroundWindow();
```

`SetForegroundWindow` brings a window to the front and gives it keyboard focus.
Windows may silently deny this if the calling process is not the foreground process —
use `AttachThreadInput` if reliable focusing is required (see advanced section).

**Get the currently focused window:**
```powershell
$hwnd = [WinAPI]::GetForegroundWindow()
```

---

### GetWindowThreadProcessId

```csharp
[DllImport("user32.dll")]
public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);
```

Maps HWND → PID. Useful when you have an HWND from enumeration and need the process:
```powershell
$pid = 0
[WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$pid)
```

---

## Getting Windows: Three Approaches

### 1. `Get-Process` (used in scripts — simplest)

```powershell
Get-Process | Where-Object {
    $_.MainWindowHandle -ne [IntPtr]::Zero -and $_.MainWindowTitle -ne ''
}
```

Returns **one window per process** (the `MainWindow`). Covers 99% of desktop management
needs. Does not enumerate secondary windows (popup dialogs, tool windows).

### 2. `EnumWindows` (all top-level windows)

```powershell
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;
public class WinEnum {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int  GetWindowText(IntPtr h,
        System.Text.StringBuilder s, int n);
    public static List<long> GetWindows() {
        var list = new List<long>();
        EnumWindows((h, l) => { if (IsWindowVisible(h)) list.Add(h.ToInt64()); return true; }, IntPtr.Zero);
        return list;
    }
}
"@ -ErrorAction SilentlyContinue

$handles = [WinEnum]::GetWindows()
```

Use this when you need child windows, tool windows, or multiple windows per process.

### 3. `FindWindow` (by class or title)

```csharp
[DllImport("user32.dll", CharSet=CharSet.Unicode)]
public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
```

Finds a specific window directly without enumeration:
```powershell
# Find Notepad by class name
$hwnd = [WinAPI]::FindWindow("Notepad", $null)

# Find by exact title
$hwnd = [WinAPI]::FindWindow($null, "Untitled - Notepad")
```

---

## Multi-Monitor Support

Get all monitors (not just primary):
```powershell
Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
foreach ($s in $screens) {
    $wa = $s.WorkingArea
    Write-Host "$($s.DeviceName): $($wa.Width)x$($wa.Height) at ($($wa.X),$($wa.Y))"
}
```

To position a window on a secondary monitor, use its `WorkingArea.X` as the X offset:
```powershell
$monitor2 = [System.Windows.Forms.Screen]::AllScreens | Where-Object { -not $_.Primary } | Select-Object -First 1
$x = $monitor2.WorkingArea.X   # e.g. 1920 for a monitor to the right
$y = $monitor2.WorkingArea.Y
```

---

## DPI Awareness

On high-DPI displays (125%, 150%, 200% scaling), `GetWindowRect` returns physical pixels
but the coordinates passed to `SetWindowPos` must also be physical pixels — so they match.
No conversion is needed unless mixing with `System.Windows.Forms` which returns logical pixels.

To get the screen DPI:
```powershell
Add-Type -AssemblyName System.Drawing
$g = [System.Drawing.Graphics]::FromHwnd([IntPtr]::Zero)
$dpi = $g.DpiX  # typically 96 (100%), 120 (125%), 144 (150%), 192 (200%)
$g.Dispose()
```

---

## Virtual Desktops (Windows 10/11)

No native PowerShell cmdlets exist. Options:

**Option 1: VirtualDesktop PowerShell module (third-party)**
```powershell
Install-Module -Name VirtualDesktop -Scope CurrentUser
Get-DesktopList
Switch-Desktop -Desktop 1
```

**Option 2: COM interface (no install, complex)**
```powershell
$shell = New-Object -ComObject "Shell.Application"
# Limited API — Switch-to only, not create/query
```

**Option 3: Keyboard shortcuts via SendKeys**
```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("^#{RIGHT}")  # Win+Ctrl+Right
```

For production virtual desktop management, the `VirtualDesktop` module is the most
reliable option. Requires one-time install per machine.

---

## Common Issues

### Window positions are wrong / off by a few pixels

Windows 10/11 adds an invisible 8px border to windows for shadow rendering. `GetWindowRect`
includes this border, so `left` may be `-8` for a maximized window. This is expected — the
scripts account for it by using the values as-is, which places windows correctly.

### SetWindowPos has no effect on maximized windows

Call `ShowWindow(hwnd, 9)` (SW_RESTORE) first to un-maximize the window before repositioning.

### Focus stealing prevention

Windows prevents background processes from calling `SetForegroundWindow` in some cases.
If reliable focus is needed, use `AttachThreadInput` to attach to the foreground thread first:

```csharp
[DllImport("user32.dll")]
public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
[DllImport("kernel32.dll")]
public static extern uint GetCurrentThreadId();
[DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
```

### Admin processes

`SetWindowPos` will fail silently on windows owned by processes running as Administrator
if the calling process is not elevated. Common example: Task Manager. This is a Windows
security restriction — no workaround without matching elevation.
