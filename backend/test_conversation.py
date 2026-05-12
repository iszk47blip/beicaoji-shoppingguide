"""
端到端对话测试脚本。
运行: python test_conversation.py
输出: test_conversation_output.txt（对话记录 + 推荐结果）
"""
import requests, json, os, sys

BASE = os.environ.get("BASE_URL", "http://localhost:8005")
SESSION_ID = "test-" + os.urandom(2).hex()
OUTPUT = os.path.join(os.path.dirname(__file__), "test_conversation_output.txt")


def send(msg: str) -> dict:
    r = requests.post(
        f"{BASE}/api/chat/send",
        json={"session_id": SESSION_ID, "message": msg},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def format_rec(rec: dict) -> list[str]:
    """Format recommendation result for output."""
    lines = []
    if not rec:
        return lines
    c = rec.get("constitution", {})
    lines.append(f"  体质类型: {c.get('constitution_type', '?')}")
    lines.append(f"  体质描述: {c.get('description', '?')}")
    lines.append(f"  匹配场景: {', '.join(rec.get('scene_tags', []))}")
    lines.append(f"  推荐商品 ({len(rec.get('bundle', []))} 件):")
    for p in rec.get("bundle", []):
        lines.append(
            f"    - [{p.get('category', '?')}] {p.get('name', '?')}"
            f" | ¥{p.get('price', 0)} | {p.get('ingredients', '')}"
        )
    return lines


# ---------------------------------------------------------------------------
# 模拟一个真实顾客的完整对话
# ---------------------------------------------------------------------------
test_persona = {
    "name": "小文",
    "screening": "都没有，身体挺健康的",
    "constitution": [
        "偏凉，冬天手脚容易冰凉",
        "偶尔上火，不算频繁",
        "还好吧，不算太累",
        "偶尔会腹胀",
        "比较怕冷，比别人穿得多",
        "睡眠时好时坏吧",
    ],
    "scene": [
        "最近睡眠不太好，而且感觉没什么精神",
        "入睡比较困难，躺床上脑子停不下来",
    ],
}

lines = []
def log(line: str = ""):
    lines.append(line)
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))


log("=" * 60)
log("  焙草集 AI 对话测试")
log(f"  服务: {BASE}")
log(f"  会话: {SESSION_ID}")
log("=" * 60)

# Step 1: 开场
log("\n[开场]")
r = send("")
log(f"  小焙: {r['message']}")
log(f"  阶段: {r['stage']}")

# Step 2: 顾客回应
log(f"\n[顾客回应]")
log(f"  顾客: 好的，帮我看看吧")
r = send("好的，帮我看看吧")
log(f"  小焙: {r['message']}")
log(f"  阶段: {r['stage']}")

# Step 3: 筛查确认
log(f"\n[安全筛查]")
log(f"  顾客: {test_persona['screening']}")
r = send(test_persona["screening"])
log(f"  小焙: {r['message']}")
log(f"  阶段: {r['stage']}  |  筛查结果: {r.get('screening_result', '-')}")

# 如果被拦截则提前结束
if r.get("screening_result") == "blocked":
    log("\n[对话终止: 安全筛查不通过]")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n测试日志已保存至: {OUTPUT}")
    sys.exit(0)

# Step 4: 告诉名字
log(f"\n[告知称呼]")
log(f"  顾客: 我叫{test_persona['name']}")
r = send(f"我叫{test_persona['name']}")
log(f"  小焙: {r['message']}")
log(f"  阶段: {r['stage']}")

# Step 5-10: 体质问答
log(f"\n[体质了解]")
for i, answer in enumerate(test_persona["constitution"]):
    log(f"  顾客: {answer}")
    r = send(answer)
    # 只显示第一句（太长的回复截断）
    msg = r["message"]
    if len(msg) > 120:
        msg = msg[:120] + "..."
    log(f"  小焙: {msg}")
    log(f"  阶段: {r['stage']}")
    if r["stage"] != "constitution":
        break

# Step 11-12: 场景描述
log(f"\n[生活困扰]")
for i, answer in enumerate(test_persona["scene"]):
    log(f"  顾客: {answer}")
    r = send(answer)
    msg = r["message"]
    if len(msg) > 120:
        msg = msg[:120] + "..."
    log(f"  小焙: {msg}")
    log(f"  阶段: {r['stage']}")

# 推荐结果
log(f"\n{'=' * 60}")
log(f"  推荐结果")
log(f"{'=' * 60}")
rec = r.get("recommendation", {})
for line in format_rec(rec):
    log(line)

# 写入文件
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n完整对话日志已保存至: {OUTPUT}")
print("可直接用记事本打开查看。")
