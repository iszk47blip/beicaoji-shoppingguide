import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, 'backend')
from app.services.tag_generator import TagGenerator

def test_generate_returns_scene_and_contra_tags():
    gen = TagGenerator()
    with patch.object(gen, '_call_llm', return_value='{"scene_tags": "补气, 健脾", "contraindication_tags": "胃寒少吃"}'):
        result = gen.generate("山药茯苓饼干", "山药、茯苓、面粉")
    assert "补气" in result["scene_tags"]
    assert "胃寒" in result["contraindication_tags"]

def test_generate_calls_correct_prompt():
    gen = TagGenerator()
    captured = {}
    def capture_prompt(prompt):
        captured["prompt"] = prompt
        return '{"scene_tags": "x", "contraindication_tags": "y"}'
    with patch.object(gen, '_call_llm', side_effect=capture_prompt):
        gen.generate("测试", "成分")
    assert "山药茯苓饼干" in captured["prompt"] or "测试" in captured["prompt"]