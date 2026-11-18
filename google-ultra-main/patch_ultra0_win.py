"""patch_ultra0_win.py —— 把 ultra0.py 改成能在 Windows + MuMu 上直接跑

改 6 处：
  1. adb 候选路径加上 MuMu / Windows 常见位置
  2. 没设备时自动 adb connect 127.0.0.1:16384 / 7555 / 16416
  3. /tmp 改成系统临时目录（Windows 没有 /tmp）
  4. curl + xz 改成 urllib + lzma（Windows 通常没有 xz）
  5. frida-server 按设备 ABI 下载（MuMu 是 x86_64，不是 arm64）
  6. root 检查：已经是 uid=0 就不再用 su
"""
import io
import re
import sys
from pathlib import Path

P = Path("ultra0.py")
src = P.read_text(encoding="utf-8")
orig = src
changes = []


def rep(old, new, label):
    global src
    if old not in src:
        changes.append(f"❌ 未命中: {label}")
        return
    src = src.replace(old, new, 1)
    changes.append(f"✅ {label}")


# ---- 1. adb 候选路径 ----
rep(
    '''ADB_CANDIDATES = [
    os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
    "/opt/homebrew/bin/adb", "/usr/local/bin/adb", "/usr/bin/adb", "adb",
]''',
    '''ADB_CANDIDATES = [
    os.environ.get("ADB_PATH", ""),
    # Windows / MuMu
    r"C:\\Program Files\\Netease\\MuMuPlayer-12.0\\shell\\adb.exe",
    r"C:\\Program Files\\Netease\\MuMuPlayerGlobal-12.0\\shell\\adb.exe",
    r"C:\\Program Files\\Netease\\MuMu\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe",
    r"C:\\Program Files\\Netease\\MuMu\\nx_main\\adb.exe",
    r"C:\\Program Files (x86)\\Netease\\MuMuPlayer-12.0\\shell\\adb.exe",
    "adb.exe", "adb",
    # macOS / Linux
    os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
    "/opt/homebrew/bin/adb", "/usr/local/bin/adb", "/usr/bin/adb",
]''',
    "adb 候选路径（含 MuMu）",
)

rep(
    '''def find_adb() -> str:
    for c in ADB_CANDIDATES:
        if c == "adb" or Path(c).exists():''',
    '''def find_adb() -> str:
    for c in ADB_CANDIDATES:
        if not c:
            continue
        if c in ("adb", "adb.exe") or Path(c).exists():''',
    "find_adb 跳过空值",
)

# ---- 2. 自动 connect ----
rep(
    '''    out = sh("devices")
    lines = [l for l in out.splitlines()[1:] if "\\tdevice" in l]
    if not lines:
        sys.exit("❌ 没有检测到设备。请插好 USB、打开「USB 调试」，在手机上点「允许」。")''',
    '''    out = sh("devices")
    lines = [l for l in out.splitlines()[1:] if "\\tdevice" in l]
    if not lines:
        # 模拟器：自动尝试常见端口
        for port in ("16384", "7555", "16416", "62001", "21503"):
            try:
                sh("connect", f"127.0.0.1:{port}", timeout=10)
            except Exception:
                pass
            out = sh("devices")
            lines = [l for l in out.splitlines()[1:] if "\\tdevice" in l]
            if lines:
                note(f"已连接模拟器 127.0.0.1:{port}")
                break
    if not lines:
        sys.exit("❌ 没有检测到设备。MuMu 请确认已启动、开了 ADB 调试（设置里），或用 ADB_PATH 指定 adb。")''',
    "自动 connect 模拟器",
)

# ---- 3. /tmp -> tempfile ----
src = src.replace('from pathlib import Path', 'from pathlib import Path\nimport tempfile', 1)
changes.append("✅ import tempfile")
rep('tmp = Path("/tmp/frida-server.xz")', 'tmp = Path(tempfile.gettempdir()) / "frida-server.xz"', "frida-server.xz 用临时目录")
rep('raw = Path("/tmp/frida-server")', 'raw = Path(tempfile.gettempdir()) / "frida-server"', "frida-server 用临时目录")
rep('tmp = Path("/tmp/module_521.apk")', 'tmp = Path(tempfile.gettempdir()) / "module_521.apk"', "module apk 用临时目录")

# ---- 4/5. frida-server 下载：按 ABI + urllib/lzma ----
old_dl = '''        url = (f"https://github.com/frida/frida/releases/download/{ver}/"
               f"frida-server-{ver}-android-arm64.xz")
        tmp = Path(tempfile.gettempdir()) / "frida-server.xz"
        subprocess.run(["curl", "-L", "-o", str(tmp), url], check=True)
        subprocess.run(["xz", "-d", "-f", str(tmp)], check=True)
        raw = Path(tempfile.gettempdir()) / "frida-server"
        sh("push", str(raw), FRIDA_REMOTE, timeout=120)
        sh("shell", f"chmod 755 {FRIDA_REMOTE}")'''
new_dl = '''        abi = sh("shell", "getprop ro.product.cpu.abi").strip() or "arm64-v8a"
        arch = {"arm64-v8a": "arm64", "armeabi-v7a": "arm", "armeabi": "arm",
                "x86_64": "x86_64", "x86": "x86"}.get(abi, "arm64")
        note(f"设备 ABI={abi} → frida-server-{ver}-android-{arch}")
        url = (f"https://github.com/frida/frida/releases/download/{ver}/"
               f"frida-server-{ver}-android-{arch}.xz")
        import urllib.request, lzma
        tmp = Path(tempfile.gettempdir()) / "frida-server.xz"
        note(f"下载 {url}")
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            f.write(r.read())
        raw = Path(tempfile.gettempdir()) / "frida-server"
        with lzma.open(tmp, "rb") as fi, open(raw, "wb") as fo:
            fo.write(fi.read())
        sh("push", str(raw), FRIDA_REMOTE, timeout=180)
        sh("shell", f"chmod 755 {FRIDA_REMOTE}")'''
rep(old_dl, new_dl, "frida-server 按 ABI 下载（urllib+lzma）")

# ---- 6. root 检查 ----
rep(
    '''def ensure_root():
    try:
        uid = sh("shell", "su -c id", timeout=15)
    except Exception:
        uid = ""
    if "uid=0" not in uid:
        sys.exit("❌ 设备没有 root 权限，脚本需要 root 才能注入。")''',
    '''def ensure_root():
    try:
        uid = sh("shell", "id", timeout=15)
    except Exception:
        uid = ""
    if "uid=0" not in uid:
        try:
            uid = sh("shell", "su -c id", timeout=15)
        except Exception:
            uid = ""
    if "uid=0" not in uid:
        sys.exit("❌ 设备没有 root 权限。MuMu 请在设置里打开「ROOT 权限」后重启模拟器。")''',
    "root 检查（先 id 再 su）",
)

if src == orig:
    print("没有任何改动，可能已经打过补丁")
else:
    P.write_text(src, encoding="utf-8")
    print("\n".join(changes))
    print("\n已写回 ultra0.py")
