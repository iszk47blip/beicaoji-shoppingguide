"""Test constitution signal extraction from free-text Chinese descriptions.

Validates whether MiniMax M2.7 can reliably extract structured constitution
signals from natural language before we commit to the B+C hybrid approach.
"""

import json
import os
import sys
from anthropic import Anthropic
from dotenv import load_dotenv

# Force UTF-8 on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

load_dotenv()

client = Anthropic(
    api_key=os.getenv("LLM_API_KEY", ""),
    base_url=os.getenv("LLM_BASE_URL", "https://api.minimaxi.com/anthropic"),
)
MODEL = os.getenv("LLM_MODEL", "MiniMax-M2.7")

EXTRACTION_SYSTEM = """你是一个中医体质信号提取器。从顾客的自然语言中提取5个体质信号字段。
你必须严格使用下面列出的选项原文，一字不差。"""

EXTRACTION_INSTRUCTION = """从以下顾客描述中提取体质信号。

顾客说：「{user_input}」

## 字段定义和可选值（必须严格使用这些字符串，一字不差）

1. temperature_tendency（寒热体感）：
   - "偏凉，冬天容易手脚冰凉"
   - "偏暖，不怎么怕冷"
   - "说不准，看情况"

2. heat_signs（上火倾向）：
   - "经常，动不动就上火"
   - "偶尔，不算频繁"
   - "几乎不"

3. qi_deficiency（气虚程度）：
   - "是，经常觉得累、不想说话"
   - "还好，正常范围内"
   - "不会，精力比较充沛"

4. damp_heat（脾胃湿热）：
   - "经常这样"
   - "偶尔"
   - "基本没有"

5. sweat_tendency（出汗情况）：
   - "稍微一动就容易出汗"
   - "正常，热了或运动了才出汗"
   - "几乎不出汗，比别人汗少"

规则：
- 对每个字段，如果顾客的话里提到了相关信息，输出最匹配的选项原文（一字不差）
- 如果信息模糊，仍输出最接近的选项原文（宁可猜错也不要留空）
- 只在完全未提及时才填空字符串 ""
- 只输出JSON，不要任何额外文字

{{"temperature_tendency": "...", "heat_signs": "...", "qi_deficiency": "...", "damp_heat": "...", "sweat_tendency": "..."}}"""

# Test cases: (user_input, expected_signals)
TEST_CASES = [
    # Clear signals — should extract well
    (
        "我冬天手脚特别凉，平时也容易累，说话都没力气",
        {"temperature_tendency": "偏凉，冬天容易手脚冰凉",
         "qi_deficiency": "是，经常觉得累、不想说话",
         "heat_signs": "", "damp_heat": "", "sweat_tendency": ""}
    ),
    (
        "我老上火，动不动就长痘、口腔溃疡，吃饭后肚子容易胀",
        {"heat_signs": "经常，动不动就上火",
         "damp_heat": "经常这样",
         "temperature_tendency": "", "qi_deficiency": "", "sweat_tendency": ""}
    ),
    (
        "稍微动一下就出一身汗，还老是上火长痘",
        {"sweat_tendency": "稍微一动就容易出汗",
         "heat_signs": "经常，动不动就上火",
         "temperature_tendency": "", "qi_deficiency": "", "damp_heat": ""}
    ),
    (
        "我觉得自己挺正常的，没什么特别不舒服的地方",
        {"temperature_tendency": "说不准，看情况",
         "heat_signs": "几乎不",
         "qi_deficiency": "不会，精力比较充沛",
         "damp_heat": "基本没有",
         "sweat_tendency": "正常，热了或运动了才出汗"}
    ),
    # Mixed / vague signals
    (
        "冬天手脚有点凉吧，但也不是特别怕冷。精力还行，偶尔会上火",
        {"temperature_tendency": "偏凉，冬天容易手脚冰凉",
         "qi_deficiency": "还好，正常范围内",
         "heat_signs": "偶尔，不算频繁",
         "damp_heat": "", "sweat_tendency": ""}
    ),
    (
        "我睡眠不太好，晚上容易醒来，白天就特别累",
        {"qi_deficiency": "是，经常觉得累、不想说话",
         "temperature_tendency": "", "heat_signs": "", "damp_heat": "", "sweat_tendency": ""}
    ),
    # Single signal
    (
        "我最大的问题就是怕冷，冬天比别人穿得多多了",
        {"temperature_tendency": "偏凉，冬天容易手脚冰凉",
         "heat_signs": "", "qi_deficiency": "", "damp_heat": "", "sweat_tendency": ""}
    ),
    (
        "吃完饭经常肚子胀，大便也不太成形",
        {"damp_heat": "经常这样",
         "temperature_tendency": "", "heat_signs": "", "qi_deficiency": "", "sweat_tendency": ""}
    ),
    # Opposite signals — should NOT extract to same constitution
    (
        "我冬天怕冷，但容易出汗，一动就出汗",
        {"temperature_tendency": "偏凉，冬天容易手脚冰凉",
         "sweat_tendency": "稍微一动就容易出汗",
         "heat_signs": "", "qi_deficiency": "", "damp_heat": ""}
    ),
    (
        "精力挺好的，冬天也不怎么怕冷",
        {"qi_deficiency": "不会，精力比较充沛",
         "temperature_tendency": "偏暖，不怎么怕冷",
         "heat_signs": "", "damp_heat": "", "sweat_tendency": ""}
    ),
    # Edge: very colloquial / regional Chinese
    (
        "我就是老上火，嘴巴干得很，还长痘痘，烦死了",
        {"heat_signs": "经常，动不动就上火",
         "temperature_tendency": "", "qi_deficiency": "", "damp_heat": "", "sweat_tendency": ""}
    ),
    (
        "我都不咋出汗，夏天别人汗流浃背我都没事，冬天手脚冰得很",
        {"sweat_tendency": "几乎不出汗，比别人汗少",
         "temperature_tendency": "偏凉，冬天容易手脚冰凉",
         "heat_signs": "", "qi_deficiency": "", "damp_heat": ""}
    ),
]


def fuzzy_match(extracted: str, expected: str) -> bool:
    """Check if extracted value matches expected, allowing minor variations."""
    if extracted == expected:
        return True
    if not extracted or not expected:
        return False
    # Remove punctuation and whitespace for comparison
    import re
    a = re.sub(r'[，。！？、\s]', '', extracted)
    b = re.sub(r'[，。！？、\s]', '', expected)
    return a == b


def test_extraction():
    total_fields = 0
    exact_matches = 0
    fuzzy_matches = 0
    results = []

    print(f"Model: {MODEL}")
    print(f"Test cases: {len(TEST_CASES)}")
    print("=" * 70)

    for i, (user_input, expected) in enumerate(TEST_CASES):
        prompt = EXTRACTION_INSTRUCTION.format(user_input=user_input)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = ""
        for block in resp.content:
            if hasattr(block, "text"):
                raw = block.text.strip()
                break

        # Parse JSON
        try:
            extracted = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            try:
                extracted = json.loads(raw)
            except json.JSONDecodeError:
                print(f"\nCase {i+1}: FAILED TO PARSE JSON")
                print(f"  Input:  {user_input}")
                print(f"  Raw:    {raw[:200]}")
                results.append({"input": user_input, "parsed": False})
                continue

        fields = ["temperature_tendency", "heat_signs", "qi_deficiency",
                   "damp_heat", "sweat_tendency"]
        case_exact = 0
        case_fuzzy = 0
        case_total = 0

        print(f"\nCase {i+1}: {user_input}")
        for field in fields:
            exp_val = expected.get(field, "")
            ext_val = extracted.get(field, "")
            case_total += 1

            if ext_val == exp_val:
                case_exact += 1
                print(f"  {field}: ✓ \"{ext_val}\"")
            elif fuzzy_match(ext_val, exp_val):
                case_fuzzy += 1
                print(f"  {field}: ~ \"{ext_val}\" (exp: \"{exp_val}\")")
            else:
                print(f"  {field}: ✗ got \"{ext_val}\", exp \"{exp_val}\"")

        total_fields += case_total
        exact_matches += case_exact
        fuzzy_matches += case_fuzzy
        results.append({
            "input": user_input,
            "parsed": True,
            "exact": case_exact,
            "fuzzy": case_fuzzy,
            "total": case_total,
            "extracted": extracted,
            "expected": expected,
        })

    print("\n" + "=" * 70)
    print(f"\nRESULTS ({len(TEST_CASES)} cases, {total_fields} fields):")
    print(f"  Exact matches:  {exact_matches}/{total_fields} = {exact_matches/total_fields*100:.1f}%")
    print(f"  Fuzzy matches:  {fuzzy_matches}/{total_fields} = {fuzzy_matches/total_fields*100:.1f}%")
    print(f"  Combined:       {exact_matches+fuzzy_matches}/{total_fields} = {(exact_matches+fuzzy_matches)/total_fields*100:.1f}%")

    # Signal-level analysis: how many signals per case
    real_signals = sum(1 for _, exp in TEST_CASES
                       for v in exp.values() if v)
    signal_exact = sum(1 for r in results if r.get("parsed")
                       for f in ["temperature_tendency", "heat_signs", "qi_deficiency",
                                  "damp_heat", "sweat_tendency"]
                       if r["expected"].get(f) and r["extracted"].get(f) == r["expected"][f])
    signal_fuzzy = sum(1 for r in results if r.get("parsed")
                       for f in ["temperature_tendency", "heat_signs", "qi_deficiency",
                                  "damp_heat", "sweat_tendency"]
                       if r["expected"].get(f) and r["extracted"].get(f)
                       and fuzzy_match(r["extracted"].get(f, ""), r["expected"].get(f, "")))

    print(f"\n  Non-empty expected signals: {real_signals}")
    if real_signals > 0:
        print(f"  Signal exact:   {signal_exact}/{real_signals} = {signal_exact/real_signals*100:.1f}%")
        print(f"  Signal fuzzy:   {signal_fuzzy}/{real_signals} = {signal_fuzzy/real_signals*100:.1f}%")

    threshold = 0.80
    combined_rate = (exact_matches + fuzzy_matches) / total_fields
    print(f"\n  Threshold for B+C: {threshold*100:.0f}%")
    print(f"  RESULT: {'PASS — proceed with B+C hybrid' if combined_rate >= threshold else 'FAIL — fall back to adaptive QA only (Approach B)'}")

    return results


if __name__ == "__main__":
    test_extraction()
