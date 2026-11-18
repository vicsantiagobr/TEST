"""run_frida_yt.py —— 单独查 YouTube Premium 附加项的 offer（拿最新 token）"""
import json
import sys
import threading
import time

import frida

import ultra0

SKUS = ["g1.youtube_premium_individual_add_on"]


def main():
    wait = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = 0
    for p in dev.enumerate_processes():
        if "subscriptions.red" in p.name or p.name == "Google One":
            pid = p.pid
            break
    if not pid:
        sys.exit("没找到 Google One 进程")
    print(f"attach pid={pid}")

    js = ultra0.build_js("5x", True)
    js = js.replace('var PRODUCTS=["g1.play.20tb"];',
                    'var PRODUCTS=' + json.dumps(SKUS) + ';', 1)

    sess = dev.attach(pid)
    done = threading.Event()
    offers = []

    def on_msg(m, d):
        p = m.get("payload") or {}
        print("  EVT", json.dumps(p, ensure_ascii=False)[:260], flush=True)
        if p.get("ev") == "offer":
            offers.append(p)
        if p.get("ev") in ("list_only", "no_trial", "query_err", "no_offers"):
            done.set()

    sc = sess.create_script(js)
    sc.on("message", on_msg)
    sc.load()
    done.wait(timeout=wait)
    time.sleep(1)

    print("\n=== YouTube 附加项 offer ===")
    for o in offers:
        print(f"  {o.get('product')} / offerId={o.get('id')} micros={o.get('micros')} period={o.get('period')}")
        print(f"    token={o.get('token')}")
    try:
        sess.detach()
    except Exception:
        pass


if __name__ == "__main__":
    main()
