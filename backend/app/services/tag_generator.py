import json
import re
import time
from anthropic import Anthropic
from app.config import settings

TAG_GENERATION_SYSTEM = "你是药食同源产品标签专家。根据产品信息生成场景标签和禁忌标签。"

TAG_GENERATION_USER = """产品名称：{name}
成分：{ingredients}

要求：
- scene_tags：适合的场景或调理方向，用有意义的词描述，2-5 个，用逗号分隔
- contraindication_tags：禁忌或需慎用的情况，如"孕妇慎用"、"胃寒少吃"、"经期慎用"，用逗号分隔，无则写"无"

只输出一行 JSON：
{{"scene_tags": "...", "contraindication_tags": "..."}}"""

class TagGenerationError(Exception):
    pass

class TagGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def generate(self, name: str, ingredients: str) -> dict:
        """Returns {"scene_tags": "...", "contraindication_tags": "..."}"""
        prompt = TAG_GENERATION_USER.format(name=name, ingredients=ingredients or "未知")
        text = self._call_llm(prompt)
        if not text:
            raise TagGenerationError("LLM 返回为空")
        try:
            text = text.strip()
            # Extract JSON from markdown code fence, or use raw text
            m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if m:
                text = m.group(1)
            else:
                text = re.sub(r'```[a-z]*\s*', '', text).strip()
            data = json.loads(text)
            return {
                "scene_tags": data.get("scene_tags", ""),
                "contraindication_tags": data.get("contraindication_tags", ""),
            }
        except json.JSONDecodeError as e:
            raise TagGenerationError(f"LLM 返回格式错误: {e.msg} — 原始内容: {text[:200]}")

    def _call_llm(self, prompt: str) -> str:
        resp = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            thinking={"type": "disabled"},
            timeout_seconds=30,
            system=TAG_GENERATION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = None
        for block in resp.content:
            if hasattr(block, "text"):
                text = block.text.strip()
                if text:
                    result_text = text
                    break
            elif hasattr(block, "thinking"):
                thinking = block.thinking or ""
                if thinking.strip() and result_text is None:
                    result_text = thinking.strip()
        if result_text:
            return result_text
        raise TagGenerationError("LLM 返回为空")