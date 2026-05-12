# backend/tests/test_report_generator.py
from app.services.report_generator import generate_report

def test_generate_report():
    report = generate_report(
        '{"qi_deficiency": "是，经常觉得累、不想说话"}',
        "睡不好",
        {"bundle": []},
        "小明"
    )
    assert report["customer_name"] == "小明"
    assert report["constitution_type"] is not None
    assert "不构成医疗诊断" in report["disclaimer"]