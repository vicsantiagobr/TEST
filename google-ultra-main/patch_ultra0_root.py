"""patch_ultra0_root.py —— 让 ultra0.py 支持「adb root 但无 su」的模拟器（MuMu）"""
from pathlib import Path

P = Path("ultra0.py")
src = P.read_text(encoding="utf-8")
orig = src
log = []


def rep(old, new, label):
    global src
    if old not in src:
        log.append(f"❌ 未命中: {label}")
        return
    src = src.replace(old, new, 1)
    log.append(f"✅ {label}")


# 1) ensure_root：先试 adb root
rep(
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
    '''def ensure_root():
    def _id():
        try:
            return sh("shell", "id", timeout=15)
        except Exception:
            return ""

    uid = _id()
    if "uid=0" not in uid:
        # 模拟器常见：adb root 把 adbd 提权，无需 su
        try:
            sh("root", timeout=20)
            time.sleep(2)
            uid = _id()
            if "uid=0" in uid:
                note("已通过 adb root 提权")
        except Exception:
            pass
    if "uid=0" not in uid:
        try:
            uid = sh("shell", "su -c id", timeout=15)
        except Exception:
            uid = ""
    if "uid=0" not in uid:
        sys.exit("❌ 设备没有 root 权限。MuMu：设置里打开「ROOT 权限」并重启；或先手动执行 adb root。")''',
    "ensure_root 支持 adb root",
)

# 2) frida-server 启动：已是 root 就不用 su
rep(
    '''    sh("shell", f"su -c 'nohup {FRIDA_REMOTE} -D >/dev/null 2>&1 &'", timeout=15)''',
    '''    is_root = "uid=0" in sh("shell", "id")
    if is_root:
        sh("shell", f"nohup {FRIDA_REMOTE} -D >/dev/null 2>&1 &", timeout=15)
    else:
        sh("shell", f"su -c 'nohup {FRIDA_REMOTE} -D >/dev/null 2>&1 &'", timeout=15)''',
    "frida-server 启动兼容无 su",
)

if src == orig:
    print("没有改动（可能已打过补丁）")
else:
    P.write_text(src, encoding="utf-8")
    print("\n".join(log))
