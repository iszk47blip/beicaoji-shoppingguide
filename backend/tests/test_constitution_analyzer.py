# backend/tests/test_constitution_analyzer.py
from app.services.constitution_analyzer import analyze

def test_analyze_qi_deficiency():
    raw = '{"qi_deficiency": "是，经常觉得累、不想说话", "temperature_tendency": "偏凉，冬天容易手脚冰凉"}'
    result = analyze(raw)
    assert result["constitution_type"] == "气虚质"

def test_analyze_balanced():
    raw = '{"qi_deficiency": "不会，精力比较充沛", "temperature_tendency": "说不准"}'
    result = analyze(raw)
    assert result["constitution_type"] == "平和质"