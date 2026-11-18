"""scan_all_offers.py —— 批量扫描候选商品 ID，列出所有 offer（含 0 元档和 token）

用法: python scan_all_offers.py [--chunk 18] [--wait 25]
"""
import argparse
import json
import threading
import time

import frida

import ultra0

CANDIDATES = [
    # 存储档（已知命名规律）
    "g1.100gb", "g1.200gb", "g1.helium", "g1.2tb", "g1.5tb", "g1.10tb", "g1.20tb", "g1.30tb",
    "g1.30gb", "g1.30gb.1month_eft",
    # AI 档
    "g1.ai", "g1.ai.pro", "g1.ai.plus", "g1.ai.ultra",
    "g1.2tb.ai", "g1.2tb.ai.subs_variant", "g1.5tb.ai", "g1.20tb.ai", "g1.30tb.ai",
    # play 前缀（带试用的那一族）
    "g1.play", "g1.play.ai", "g1.play.2tb", "g1.play.5tb", "g1.play.20tb", "g1.play.30tb",
    "g1.play.ai.pro", "g1.play.ai.plus", "g1.play.ai.ultra", "g1.play.helium", "g1.play.pro", "g1.play.plus",
    # 促销后缀组合
    "g1.2tb.3months_ip_85p.acq", "g1.5tb.3months_ip_75p.acq", "g1.100gb.3months_ip_83p.acq",
    "g1.200gb.3months_ip_83p.acq", "g1.helium.3months_ip_83p.acq",
    "g1.2tb.12months_eft", "g1.30tb.12months_eft", "g1.20tb.12months_eft",
    "g1.2tb.1month_eft", "g1.30tb.1month_eft",
    "g1.play.20tb.12month", "g1.play.ai.pro.12month",
    # 附加项
    "g1.youtube_premium_individual_add_on", "g1.youtube_premium_family_add_on",
    "g1.home_premium", "g1.health_premium", "g1.play.home", "g1.play.health",
    # Ultra 变体
    "g1.ultra", "g1.ultra.20tb", "g1.ultra.30tb", "g1.pro", "g1.plus", "g1.premium",
]


def run_chunk(dev, pid, products, wait):
    js = ultra0.build_js("5x", True)
    js = js.replace('var PRODUCTS=["g1.play.20tb"];', 'var PRODUCTS=' + json.dumps(products) + ';', 1)
    sess = dev.attach(pid)
    done = threading.Event()
    offers, products_seen, errs = [], [], []

    def on_msg(m, d):
        p = m.get("payload") or {}
        ev = p.get("ev")
        if ev == "offer":
            offers.append(p)
        elif ev == "pd":
            products_seen.append(p.get("n"))
        elif ev and ("err" in str(ev)):
            errs.append(p)
        elif ev in ("list_only", "no_trial", "query_err", "no_offers"):
            done.set()

    sc = sess.create_script(js)
    sc.on("message", on_msg)
    sc.load()
    done.wait(timeout=wait)
    time.sleep(0.5)
    try:
        sess.detach()
    except Exception:
        pass
    return offers, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=18)
    ap.add_argument("--wait", type=int, default=25)
    a = ap.parse_args()

    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = 0
    for p in dev.enumerate_processes():
        if "subscriptions.red" in p.name or p.name == "Google One":
            pid = p.pid
            break
    if not pid:
        raise SystemExit("没找到 Google One 进程")

    all_offers = []
    for i in range(0, len(CANDIDATES), a.chunk):
        part = CANDIDATES[i:i + a.chunk]
        print(f"\n=== 批次 {i//a.chunk + 1}: 查询 {len(part)} 个 ID ===", flush=True)
        offers, errs = run_chunk(dev, pid, part, a.wait)
        print(f"    返回 offer 事件 {len(offers)} 条", flush=True)
        all_offers.extend(offers)

    # 汇总
    print("\n" + "=" * 78)
    print("所有有免费档的 offer（micros == 0）：")
    print("=" * 78)
    seen = set()
    for o in all_offers:
        if str(o.get("micros")) != "0":
            continue
        key = (o.get("product"), o.get("id"), o.get("token"))
        if key in seen:
            continue
        seen.add(key)
        print(f"  {o.get('product'):34s} offer={str(o.get('id')):12s} period={o.get('period'):4s}")
        print(f"      token={o.get('token')}")

    print("\n" + "=" * 78)
    print("所有返回过的商品（含原价）：")
    print("=" * 78)
    prods = {}
    for o in all_offers:
        prods.setdefault(o.get("product"), []).append(o)
    for pid_, lst in sorted(prods.items()):
        free = sum(1 for x in lst if str(x.get("micros")) == "0")
        print(f"  {pid_:34s} offer数={len(lst):2d}  免费档={free}")

    with open("scan_offers_result.json", "w", encoding="utf-8") as f:
        json.dump(all_offers, f, ensure_ascii=False, indent=2)
    print("\n[+] 明细已写入 scan_offers_result.json")


if __name__ == "__main__":
    main()
