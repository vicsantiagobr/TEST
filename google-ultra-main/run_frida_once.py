"""run_frida_once.py —— 手动跑一次注入，把所有事件打印出来（排错用）

用法: python run_frida_once.py [--plan 5x|20x|auto] [--pid 7694] [--wait 30]
"""
import argparse
import json
import sys
import threading
import time

import frida

import ultra0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="5x", choices=["auto", "5x", "20x"])
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--wait", type=int, default=30)
    ap.add_argument("--list", action="store_true", default=True)
    a = ap.parse_args()

    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = a.pid
    if not pid:
        for p in dev.enumerate_processes():
            if "subscriptions.red" in p.name or p.name == "Google One":
                pid = p.pid
                break
    if not pid:
        sys.exit("没找到 Google One 进程，先在模拟器里打开它")
    print(f"attach pid={pid}")

    sess = dev.attach(pid)
    js = ultra0.build_js(a.plan, True)
    open("build_debug.js", "w", encoding="utf-8").write(js)
    print("已写出 build_debug.js（可对照检查）")

    events = []
    done = threading.Event()

    def on_msg(m, data):
        p = m.get("payload") or {}
        events.append(p)
        print("  EVT", json.dumps(p, ensure_ascii=False)[:300], flush=True)
        if p.get("ev") in ("list_only", "no_trial", "query_err", "no_offers"):
            done.set()

    def on_err(e):
        print("  ERR", e, flush=True)

    sc = sess.create_script(js)
    sc.on("message", on_msg)
    sc.on("destroyed", lambda: print("  script destroyed"))
    sc.load()
    print("script loaded, 等待事件…")
    done.wait(timeout=a.wait)
    time.sleep(1)
    print(f"\n共 {len(events)} 个事件")
    for e in events:
        if e.get("ev") == "offer":
            print(f"  offer {e.get('product')} / {e.get('id')} micros={e.get('micros')} period={e.get('period')}")
            print(f"    token={e.get('token')}")
    try:
        sess.detach()
    except Exception:
        pass


if __name__ == "__main__":
    main()
