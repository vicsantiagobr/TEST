"""patch_ultra0_list.py —— 给 ultra0.py 加 --list：只查 offer + 打印 token，不拉起收银台

用途：先看清楚 12 个月 offer 在不在、token 是什么，确认无误再决定要不要真下单。
"""
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


# 1) build_js 支持 list_only
rep(
    '''def build_js(plan: str = "auto") -> str:
    """按 plan 选择要查询的商品：5x=20TB，20x=30TB（隐藏带试用 ID）。"""
    js = FRIDA_JS''',
    '''def build_js(plan: str = "auto", list_only: bool = False) -> str:
    """按 plan 选择要查询的商品：5x=20TB，20x=30TB（隐藏带试用 ID）。"""
    js = FRIDA_JS
    if list_only:
        js = js.replace('var PREFER="";', 'var PREFER=""; var LIST_ONLY=true;', 1)''',
    "build_js 支持 list_only",
)

# 2) JS 里：命中后如果是 list 模式就只上报、不拉起收银台
rep(
    "      launch(best.pd, best.offer);",
    '''      if (typeof LIST_ONLY !== "undefined" && LIST_ONLY) {
        S({ev:"list_only", product:best.product, id:best.id, period:best.period, token:best.token});
        return;
      }
      launch(best.pd, best.offer);''',
    "JS 加 list_only 分支",
)

# 3) run_trial 透传
rep(
    'def run_trial(pid: int, wait=90, plan="auto") -> dict:',
    'def run_trial(pid: int, wait=90, plan="auto", list_only=False) -> dict:',
    "run_trial 签名",
)
rep(
    "    sc = sess.create_script(build_js(plan))",
    "    sc = sess.create_script(build_js(plan, list_only))",
    "run_trial 传参",
)

# 4) process 支持 list_only 并跳过账号校验
rep(
    'def process(email, password="", totp_secret="", add=True, card=None, plan="auto", no_switch=False) -> dict:',
    'def process(email, password="", totp_secret="", add=True, card=None, plan="auto", no_switch=False, list_only=False) -> dict:',
    "process 签名",
)
rep(
    '''    if no_switch:
        cur = current_play_account()
        if cur != email.lower():
            warn(f"当前 Play 账号是 {cur or '未知'}，不是 {email}，中止")
            rec["status"] = "wrong_account"
            return rec
        ok("Play 账号已确认（手动切换模式）")
    elif not switch_play(email):''',
    '''    if list_only:
        cur = current_play_account()
        ok(f"列表模式：使用设备当前账号 {cur or '未知'}（不校验、不下单）")
    elif no_switch:
        cur = current_play_account()
        if cur != email.lower():
            warn(f"当前 Play 账号是 {cur or '未知'}，不是 {email}，中止")
            rec["status"] = "wrong_account"
            return rec
        ok("Play 账号已确认（手动切换模式）")
    elif not switch_play(email):''',
    "process 跳过账号校验",
)
rep(
    "    fr = run_trial(pid, plan=plan)",
    "    fr = run_trial(pid, plan=plan, list_only=list_only)",
    "process 传 list_only",
)
rep(
    '''    if fr["launched"] and fr["launched"].get("code") == 0:''',
    '''    if list_only:
        rec["status"] = "listed"
        return rec
    if fr["launched"] and fr["launched"].get("code") == 0:''',
    "process list 模式直接返回",
)

# 5) main 加 --list
rep(
    '''    ap.add_argument("--check", action="store_true", help="只做环境自检")''',
    '''    ap.add_argument("--check", action="store_true", help="只做环境自检")
    ap.add_argument("--list", action="store_true", help="只列出 offer 和 token，不拉起收银台（零风险）")''',
    "main 加 --list 参数",
)
rep(
    '''            rec = process(email, pw, sec, add=not a.no_add, card=card, plan=a.plan,
                          no_switch=a.no_switch)''',
    '''            rec = process(email, pw, sec, add=not a.no_add, card=card, plan=a.plan,
                          no_switch=a.no_switch, list_only=a.list)''',
    "main 传 list_only",
)

# 6) --list 时允许不给账号：用占位邮箱
rep(
    '''    if a.account:
        parts = a.account.split(":")''',
    '''    if a.list and not a.account and not a.accounts:
        a.account = "current@device"
    if a.account:
        parts = a.account.split(":")''',
    "--list 允许省略账号",
)

if src == orig:
    print("没有改动（可能已打过补丁）")
else:
    P.write_text(src, encoding="utf-8")
    print("\n".join(log))
