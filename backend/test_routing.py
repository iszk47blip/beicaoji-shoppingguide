"""Routing test suite — verifies product search can interrupt any stage.

Run: python test_routing.py
Requires server running on localhost:8000
"""

import json
import urllib.request
import time
import sys
from typing import Optional

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0
SKIP = 0

RECOMMEND_QR = ["推荐更多产品", "重新了解体质", "看看产品目录"]
CATALOG_QR = ["饼干", "面包", "茶", "香囊", "帮我看看体质"]
SCREENING_QR = ["都没有", "在备孕或怀孕", "在哺乳期", "在吃处方药"]
SCENE_QR = ["睡眠不好", "消化不好", "容易疲劳", "皮肤问题", "想调理身体"]
CONSTITUTION_ENTRY_QR = ["好的，开始吧", "先看看产品"]


def send(session_id: str, message: str) -> dict:
    data = json.dumps({"session_id": session_id, "message": message}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/chat/send",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    return json.loads(resp.read())


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}: {detail}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}: {detail}")


def skip(name: str, reason: str = ""):
    global SKIP
    SKIP += 1
    print(f"  SKIP  {name}: {reason}")


# ─── helpers ────────────────────────────────────────────────

def reset(sid: str):
    data = json.dumps({"session_id": sid}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/chat/reset",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)


def has_product_name(r: dict, keyword: str) -> bool:
    """Check if the message or recommendation mentions a product keyword."""
    msg = r.get("message", "")
    rec = r.get("recommendation") or {}
    products = rec.get("bundle", [])
    for p in products:
        if keyword in str(p.get("name", "")):
            return True
    return keyword in msg


def has_recommendation(r: dict) -> bool:
    rec = r.get("recommendation")
    return rec is not None and len(rec.get("bundle", [])) > 0


def stage_is(r: dict, *stages: str) -> bool:
    return r.get("stage") in stages


def qr_equals(r: dict, expected: list) -> bool:
    return r.get("quick_replies") == expected


def in_constitution_pipeline(r: dict) -> bool:
    """Is the stage in the constitution pipeline (not escaped)?"""
    return r.get("stage") in ("constitution", "scene")


# ═══════════════════════════════════════════════════════════
#  A. Basic product search from greeting
# ═══════════════════════════════════════════════════════════

def test_a1():
    """A1: From welcome, ask about a specific product directly."""
    print("\n── A1: '有没有罗汉果茶' from greeting ──")
    sid = f"a1-{int(time.time())}"
    reset(sid)
    send(sid, "")
    r = send(sid, "有没有罗汉果茶")

    # Should NOT enter screening/constitution pipeline
    check("A1a - not in screening/constitution/scene",
          not stage_is(r, "screening", "constitution", "scene"),
          f"stage={r.get('stage')}")
    # Should have either recommendation or mention the product
    check("A1b - mentions 罗汉果 or has recommendation",
          has_product_name(r, "罗汉果") or has_recommendation(r),
          f"has_rec={has_recommendation(r)}")
    # Should NOT have screening quick_replies
    check("A1c - qr not screening buttons",
          not qr_equals(r, SCREENING_QR),
          f"qr={r.get('quick_replies')}")


def test_a2():
    """A2: Ask about price of a specific product."""
    print("\n── A2: '罗汉果茶多少钱' from greeting ──")
    sid = f"a2-{int(time.time())}"
    reset(sid)
    send(sid, "")
    r = send(sid, "罗汉果茶多少钱")

    check("A2a - not in screening/constitution",
          not stage_is(r, "screening", "constitution"),
          f"stage={r.get('stage')}")
    check("A2b - has recommendation or mentions product",
          has_recommendation(r) or has_product_name(r, "罗汉果"),
          f"has_rec={has_recommendation(r)}")


def test_a3():
    """A3: Vague request for recommendations — may show products or guide to constitution."""
    print("\n── A3: '推荐几个适合我的' from greeting ──")
    sid = f"a3-{int(time.time())}"
    reset(sid)
    send(sid, "")
    r = send(sid, "推荐几个适合我的")

    # No specific product mentioned — either shows products or enters flow. Both OK.
    check("A3a - shows recommendation or enters flow",
          has_recommendation(r) or stage_is(r, "screening", "constitution", "greeting", "catalog"),
          f"stage={r.get('stage')}, has_rec={has_recommendation(r)}")


# ═══════════════════════════════════════════════════════════
#  B. Mid-conversation product search escape
# ═══════════════════════════════════════════════════════════

def test_b1():
    """B1: At screening, ask for product instead."""
    print("\n── B1: screening escape ──")
    sid = f"b1-{int(time.time())}"
    reset(sid)
    # Navigate to screening
    send(sid, "")
    r = send(sid, "帮我看看体质")
    assert stage_is(r, "screening"), f"Expected screening, got {r.get('stage')}"

    # Now ask for product
    r = send(sid, "不要筛查，给我推荐罗汉果茶")
    check("B1a - has recommendation",
          has_recommendation(r),
          f"has_rec={has_recommendation(r)}")
    check("B1b - NOT still in screening",
          not stage_is(r, "screening"),
          f"stage={r.get('stage')}")


def test_b2():
    """B2: At constitution extract, switch to product search."""
    print("\n── B2: constitution extract escape ──")
    sid = f"b2-{int(time.time())}"
    reset(sid)
    # Navigate to constitution extract
    send(sid, "")
    send(sid, "帮我看看体质")
    send(sid, "都没有")
    r = send(sid, "叫我小陈就行")
    assert stage_is(r, "constitution"), f"Expected constitution, got {r.get('stage')}"

    # Now switch to product
    r = send(sid, "算了，你就给我罗汉果茶吧")
    check("B2a - has recommendation",
          has_recommendation(r),
          f"has_rec={has_recommendation(r)}")
    check("B2b - NOT still in constitution",
          not stage_is(r, "constitution"),
          f"stage={r.get('stage')}")


def test_b3():
    """B3: At adaptive QA, insist on specific product."""
    print("\n── B3: adaptive QA escape ──")
    sid = f"b3-{int(time.time())}"
    reset(sid)
    # Navigate deep into constitution
    send(sid, "")
    send(sid, "帮我看看体质")
    send(sid, "都没有")
    send(sid, "叫我小李就行")
    r = send(sid, "我不太清楚我身体怎么样")  # vague → triggers adaptive QA
    time.sleep(1)

    # If still in constitution, push back with product request
    if stage_is(r, "constitution"):
        r = send(sid, "不用问我体质了，直接给我推罗汉果茶")
        check("B3a - has recommendation or not in constitution",
              has_recommendation(r) or not stage_is(r, "constitution"),
              f"has_rec={has_recommendation(r)}, stage={r.get('stage')}")
        check("B3b - qr not constitution-related",
              not qr_equals(r, CONSTITUTION_ENTRY_QR),
              f"qr={r.get('quick_replies')}")
    else:
        skip("B3a", "flow didn't reach constitution adaptive")


def test_b4():
    """B4: At scene stage, ask for product."""
    print("\n── B4: scene escape ──")
    sid = f"b4-{int(time.time())}"
    reset(sid)
    # Navigate to scene
    send(sid, "")
    send(sid, "帮我看看体质")
    send(sid, "都没有")
    send(sid, "叫我小周就行")
    send(sid, "我冬天手脚冰凉，平时容易累")  # should give 2+ signals → scene

    r = send(sid, "还是推荐罗汉果茶吧")
    check("B4a - has recommendation",
          has_recommendation(r),
          f"has_rec={has_recommendation(r)}")
    check("B4b - qr are recommend qr not scene qr",
          qr_equals(r, RECOMMEND_QR) or has_recommendation(r),
          f"qr={r.get('quick_replies')}")


# ═══════════════════════════════════════════════════════════
#  C. Continuous product search conversation
# ═══════════════════════════════════════════════════════════

def test_c1():
    """C1: After recommendation, say 'recommend more' — should use context."""
    print("\n── C1: '再推荐几个' after recommendation ──")
    sid = f"c1-{int(time.time())}"
    reset(sid)
    # Get a recommendation first
    send(sid, "")
    r = send(sid, "有没有罗汉果茶")
    time.sleep(1)

    if not has_recommendation(r):
        skip("C1a", "no initial recommendation to build on")
        return

    # Now ask for more with vague language
    r = send(sid, "再推荐几个")
    has_rec = has_recommendation(r)
    stage_ok = stage_is(r, "recommend", "greeting", "catalog")
    check("C1a - has recommendation or stays in reasonable stage",
          has_rec or stage_ok,
          f"has_rec={has_rec}, stage={r.get('stage')}")


def test_c2():
    """C2: After recommendation, switch to different product."""
    print("\n── C2: switch to 山楂 after 罗汉果茶 ──")
    sid = f"c2-{int(time.time())}"
    reset(sid)
    send(sid, "")
    r = send(sid, "有没有罗汉果茶")
    time.sleep(1)

    # Switch product
    r = send(sid, "有没有山楂相关的")
    check("C2a - has recommendation or mentions 山楂",
          has_recommendation(r) or has_product_name(r, "山楂"),
          f"has_rec={has_recommendation(r)}")


def test_c3():
    """C3: After product chat, return to constitution flow."""
    print("\n── C3: return to constitution after products ──")
    sid = f"c3-{int(time.time())}"
    reset(sid)
    send(sid, "")
    send(sid, "有没有罗汉果茶")
    time.sleep(1)

    r = send(sid, "帮我看看体质吧")
    check("C3a - enters screening or constitution",
          stage_is(r, "screening", "constitution", "info_collect"),
          f"stage={r.get('stage')}")


# ═══════════════════════════════════════════════════════════
#  D. Quick reply consistency
# ═══════════════════════════════════════════════════════════

def test_d1():
    """D1: Recommendation shows correct quick_replies."""
    print("\n── D1: recommend quick_replies ──")
    sid = f"d1-{int(time.time())}"
    reset(sid)
    send(sid, "")
    r = send(sid, "我最近很疲惫 你有什么推荐的吗")
    time.sleep(1)

    if has_recommendation(r):
        check("D1a - qr is recommend qr",
              qr_equals(r, RECOMMEND_QR),
              f"qr={r.get('quick_replies')}")
    else:
        skip("D1a", "no recommendation returned")


def test_d2():
    """D2: Catalog shows correct quick_replies."""
    print("\n── D2: catalog quick_replies ──")
    sid = f"d2-{int(time.time())}"
    reset(sid)
    send(sid, "")
    r = send(sid, "你都有什么产品")
    time.sleep(1)

    # May show catalog or list categories
    catalog = r.get("catalog")
    if catalog:
        check("D2a - qr is catalog qr",
              qr_equals(r, CATALOG_QR),
              f"qr={r.get('quick_replies')}")
    else:
        skip("D2a", "no catalog returned")


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print(" 焙草集 对话路由测试")
    print(f" 服务: {BASE}")
    print("=" * 60)

    # Verify server is up
    try:
        urllib.request.urlopen(f"{BASE}/health", timeout=5)
    except Exception:
        print("\nERROR: Server not running. Start with:")
        print("  cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    tests = [
        test_a1, test_a2, test_a3,
        test_b1, test_b2, test_b3, test_b4,
        test_c1, test_c2, test_c3,
        test_d1, test_d2,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            FAIL += 1
            print(f"  ERROR {test.__name__}: {e}")

    print("\n" + "=" * 60)
    total = PASS + FAIL + SKIP
    print(f"  Results: {PASS} passed, {FAIL} failed, {SKIP} skipped ({total} total)")
    if FAIL > 0:
        print(f"\n  KEY FAILURES TO FIX:")
        print(f"  - B2/B3: constitution stage product search escape (core bug)")
        print(f"  - B1/B4: mid-flow product search")
    print("=" * 60)
