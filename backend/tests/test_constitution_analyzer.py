# backend/tests/test_constitution_analyzer.py
from app.services.constitution_analyzer import analyze

def test_analyze_qi_deficiency():
    raw = '{"qi_deficiency": "是，经常觉得累、不想说话", "temperature_tendency": "偏凉，冬天容易手脚冰凉"}'
    result = analyze(raw)
    assert result["constitution_type"] == "气虚质"

def test_analyze_yang_deficiency():
    raw = '{"temperature_tendency": "偏凉，冬天容易手脚冰凉", "sweat_tendency": "几乎不出汗，比别人汗少"}'
    result = analyze(raw)
    assert result["constitution_type"] == "阳虚质"

def test_analyze_yin_deficiency():
    raw = '{"heat_signs": "经常，动不动就上火", "sweat_tendency": "稍微一动就容易出汗"}'
    result = analyze(raw)
    assert result["constitution_type"] == "阴虚质"

def test_analyze_damp_heat():
    raw = '{"damp_heat": "经常这样", "heat_signs": "经常，动不动就上火"}'
    result = analyze(raw)
    assert result["constitution_type"] == "湿热质"

def test_analyze_phlegm_damp():
    raw = '{"stool_digest": "大便容易黏滞或不成形", "damp_heat": "经常这样"}'
    result = analyze(raw)
    assert result["constitution_type"] == "痰湿质"

def test_analyze_blood_stasis():
    raw = '{"blood_combined": "经常瘀青"}'
    result = analyze(raw)
    assert result["constitution_type"] == "血瘀质"

def test_analyze_blood_stasis_both():
    """两项都有或一项经常 → 血瘀质"""
    raw = '{"blood_combined": "经常瘀青或眼前发黑（两项都有或一项经常）"}'
    result = analyze(raw)
    assert result["constitution_type"] == "血瘀质"

def test_analyze_blood_deficiency():
    raw = '{"blood_combined": "经常眼前发黑"}'
    result = analyze(raw)
    assert result["constitution_type"] == "血虚质"

def test_analyze_qi_stagnation():
    raw = '{"emotion": "经常情绪波动大"}'
    result = analyze(raw)
    assert result["constitution_type"] == "气郁质"

def test_analyze_tebin():
    raw = '{"allergy": "经常过敏"}'
    result = analyze(raw)
    assert result["constitution_type"] == "特禀质"

def test_analyze_balanced():
    """所有体质字段都是否定/中性回答 → 平和质零分fallback"""
    raw = '{"qi_deficiency": "不会，精力比较充沛", "temperature_tendency": "说不准", "heat_signs": "几乎不", "damp_heat": "基本没有", "sweat_tendency": "正常，热了或运动了才出汗", "allergy": "几乎没有", "emotion": "情绪比较稳定", "stool_digest": "大便正常", "blood_combined": "几乎没有"}'
    result = analyze(raw)
    assert result["constitution_type"] == "平和质"

def test_analyze_balanced_no_fields():
    """完全无信号 → 平和质零分fallback"""
    raw = '{}'
    result = analyze(raw)
    assert result["constitution_type"] == "平和质"

def test_analyze_mixed_signals_top_score_wins():
    """气虚质信号最强（2个），超过血虚质（1个）"""
    raw = '{"qi_deficiency": "是，经常觉得累、不想说话", "temperature_tendency": "偏凉，冬天容易手脚冰凉", "blood_combined": "经常眼前发黑"}'
    result = analyze(raw)
    assert result["constitution_type"] == "气虚质"

def test_analyze_tie_uses_first():
    """平分时取字典序第一个体质"""
    raw = '{"temperature_tendency": "偏凉，冬天容易手脚冰凉", "sweat_tendency": "几乎不出汗，比别人汗少"}'
    result = analyze(raw)
    assert result["constitution_type"] == "阳虚质"

def test_analyze_blood_combined_single_score():
    """Bug 1 regression: blood_combined 单信号正确计1分"""
    raw = '{"blood_combined": "经常瘀青"}'
    result = analyze(raw)
    assert result["constitution_type"] == "血瘀质"

def test_analyze_blood_combined_long_option():
    """Bug 1 regression: 长选项精确匹配只计1分"""
    raw = '{"blood_combined": "经常瘀青或眼前发黑（两项都有或一项经常）"}'
    result = analyze(raw)
    assert result["constitution_type"] == "血瘀质"

def test_analyze_invalid_answer_filtered():
    """Bug 2 regression: 带"我"字的非精确答案被过滤"""
    raw = '{"blood_combined": "我经常瘀青"}'
    result = analyze(raw)
    assert result["constitution_type"] == "平和质"

def test_analyze_unknown_field_ignored():
    """Bug 2 regression: 不存在的field被忽略，有效字段正常计分"""
    raw = '{"unknown_field": "随便填", "blood_combined": "经常瘀青"}'
    result = analyze(raw)
    assert result["constitution_type"] == "血瘀质"