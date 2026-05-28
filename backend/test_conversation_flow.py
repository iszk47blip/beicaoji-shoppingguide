"""
C+A 测试脚本：对话流程完整性 + 数据一致性验证
用法: python test_conversation_flow.py
"""

import requests
import sqlite3
import json
import uuid
import time
from pathlib import Path

BASE = "http://localhost:8002/api"
DB_PATH = str(Path(__file__).parent.parent / "beicaoji.db")


def new_session():
    return f"test_{uuid.uuid4().hex[:8]}_{int(time.time())}"


def send(session_id, message=""):
    r = requests.post(f"{BASE}/chat/send", json={"session_id": session_id, "message": message}, timeout=30)
    r.raise_for_status()
    return r.json()


def db_check_conv(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, stage, messages_history, stage_history,
               constitution_type, screening_result, scene_input
        FROM conversations ORDER BY id DESC LIMIT 1
    """)
    cols = [col[0] for col in c.description]
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(zip(cols, row))
    d["messages_history"] = json.loads(d["messages_history"] or "[]")
    d["stage_history"] = json.loads(d["stage_history"] or "[]")
    return d


def verify_field(name, actual, expected):
    if expected is ...:
        return True, ""
    if actual == expected:
        return True, f"[OK] {name}: {actual}"
    else:
        return False, f"[FAIL] {name}: expected {expected}, got {actual}"


def check(prefix, result, checks):
    msgs, all_ok = [], True
    for name, expected in checks.items():
        if expected is ...:
            continue
        ok, msg = verify_field(name, result.get(name), expected)
        msgs.append(msg)
        if not ok:
            all_ok = False
    return all_ok, "\n".join(msgs)


def test_scenario(name, sid, steps, verbose=True):
    if verbose:
        print(f"\n{'='*60}\n场景: {name}\n{'='*60}")

    errors = []
    for i, (message, resp_checks, db_checks) in enumerate(steps):
        label = f"步骤{i+1}" if message else f"步骤{i+1}(空消息)"
        try:
            result = send(sid, message)
        except Exception as e:
            errors.append(f"{label}: {e}")
            continue
        if resp_checks:
            ok, msg = check(label, result, resp_checks)
            if verbose:
                print(f"\n{label}: stage={result.get('stage')} phase={result.get('constitution_phase')}")
            if not ok:
                errors.append(f"{label}: {msg}")
        time.sleep(0.1)
        dbc = db_check_conv(sid)
        if db_checks and dbc:
            db_ok, db_msg = check(label, dbc, db_checks)
            if not db_ok:
                errors.append(f"{label} DB: {db_msg}")

    if verbose:
        print(f"\n[PASS] 通过" if not errors else f"\n[FAIL] 失败 ({len(errors)}): " + "; ".join(errors))
    return len(errors) == 0, errors


def run_all_tests():
    results = []

    # 场景 1: 欢迎→筛查→体质描述
    sid = new_session()
    results.append(test_scenario("1. 欢迎→筛查→体质自由描述", sid, [
        ("了解我的体质", {"stage": "screening"}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {"screening_result": "cleared"}),
        ("睡眠不好", {"stage": "constitution"}, {}),
    ]))

    # 场景 2: 体质描述→确认体质（Q1→Q2→recommend）
    sid = new_session()
    results.append(test_scenario("2. 体质描述→鉴别问题→确认体质", sid, [
        ("了解我的体质", {}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {"screening_result": "cleared"}),
        ("我最近总觉得累，睡不好", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("", {"stage": "constitution"}, {}),
        ("", {"stage": "constitution"}, {}),
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {}, {}),  # LLM may finish differential early, transition point is non-deterministic
        ("随便", {"stage": "recommend", "constitution_phase": "done"}, {}),
    ]))

    # 场景 3: 确认体质→推荐（8×空→Q1→Q2→recommend）
    sid = new_session()
    results.append(test_scenario("3. 确认体质→选择困扰→推荐", sid, [
        ("了解我的体质", {}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {"screening_result": "cleared"}),
        ("我最近总觉得累", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        * [("", {"stage": "constitution"}, {}) for _ in range(8)],
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {}, {}),  # LLM may finish differential early, transition point is non-deterministic
        ("随便", {"stage": "recommend", "constitution_phase": "done"}, {}),
        ("", {}, {}),
    ]))

    # 场景 4: 随便聊聊→Q1→Q2→recommend
    sid = new_session()
    results.append(test_scenario("4. 随便聊聊→直接推荐", sid, [
        ("了解我的体质", {}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {}),
        ("随便聊聊", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        * [("", {"stage": "constitution"}, {}) for _ in range(9)],
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "recommend", "constitution_phase": "done"}, {}),
        ("", {}, {}),
    ]))

    # 场景 5: 睡眠不好→确认体质→推荐
    # heat_signs被"疲劳"填满 → 第1个随便直接成为第2问 → 第12步转recommend
    sid = new_session()
    results.append(test_scenario("5. 睡眠不好→确认体质→推荐", sid, [
        ("了解我的体质", {}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {}),
        ("睡眠不好", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("疲劳", {}, {}),
        * [("", {"stage": "constitution"}, {}) for _ in range(7)],
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "recommend", "constitution_phase": "done"}, {}),
        ("", {}, {}),
    ]))

    # 场景 6: 推荐产品 intent
    sid = new_session()
    results.append(test_scenario("6. 推荐产品 intent", sid, [
        ("了解我的体质", {}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {}),
        ("睡眠不好", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("疲劳", {}, {}),
        * [("", {"stage": "constitution"}, {}) for _ in range(7)],
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "recommend", "constitution_phase": "done"}, {}),
        ("", {}, {}),
        ("推荐产品", {}, {}),
    ]))

    # 场景 7: 备孕 blocked
    sid = new_session()
    results.append(test_scenario("7. 筛查阶段用户说'在备孕'被 blocked", sid, [
        ("了解我的体质", {}, {}),
        ("在备孕或怀孕", {"stage": "done", "screening_result": "blocked"}, {"screening_result": "blocked"}),
    ]))

    # 场景 8: 完整对话+DB验证
    sid = new_session()
    results.append(test_scenario("8. 完整对话：欢迎→推荐全程+DB验证", sid, [
        ("了解我的体质", {"stage": "screening"}, {}),
        ("都没有", {"stage": "constitution", "screening_result": "cleared"}, {"screening_result": "cleared", "stage_history": ...}),
        ("我最近总觉得累睡不好", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        * [("", {"stage": "constitution"}, {}) for _ in range(8)],
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "constitution", "constitution_phase": "differential"}, {}),
        ("随便", {"stage": "recommend", "constitution_phase": "done"}, {}),
        ("", {}, {}),
    ]))

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}\n测试汇总: 通过 {passed}/{total}\n{'='*60}")
    for i, (ok, errors) in enumerate(results, 1):
        print(f"  {'[PASS]' if ok else '[FAIL]'} 场景{i}")
        if not ok:
            for e in errors:
                print(f"    - {e}")
    return passed == total


if __name__ == "__main__":
    import sys
    ok = run_all_tests()
    sys.exit(0 if ok else 1)