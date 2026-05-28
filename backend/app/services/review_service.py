import json
import re
from datetime import datetime, timedelta, timezone
from anthropic import Anthropic
from app.config import settings
from app.models.conversation import Conversation
from app.models.review_result import ReviewResult

REVIEW_SYSTEM_PROMPT = """你是门店AI助手的质检员。审核对话记录，找出AI回复的问题并给出改进建议。

关注以下维度：
1. 安全筛查：是否正确处理了禁忌人群（孕妇、哺乳期等）
2. 体质判断：是否准确捕捉了顾客的信号
3. 推荐准确性：推荐的产品是否与体质、困扰匹配
4. 服务态度：回复是否自然、温和、专业
5. 流程完整：是否走完了必要的筛查→体质→困扰→推荐流程

你必须严格输出以下JSON格式，不要添加任何解释或markdown：
{
  "problems": [
    {"severity": "high", "category": "安全", "description": "具体问题", "conversation_index": 1}
  ],
  "suggestions": [
    {"category": "话术", "description": "改进建议"}
  ],
  "quality_score": 8
}

注意：
- problems数组中每个元素必须是对象，包含severity/category/description/conversation_index四个字段
- severity只能是high/medium/low
- category只能是安全/推荐/态度/流程
- quality_score是1-10的整数
- 如果没有任何问题，problems和suggestions可以为空数组[]
- 不要输出任何JSON之外的文字"""

BATCH_SIZE = 5


class ReviewService:
    def __init__(self):
        self.client = Anthropic(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    def review_conversations(self, db, days: int = 1) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        convs = db.query(Conversation).filter(
            Conversation.created_at >= since,
            Conversation.messages_history.isnot(None)
        ).all()

        if not convs:
            return {"reviewed": 0, "problems_found": [], "suggestions": []}

        all_problems = []
        all_suggestions = []
        total_score = 0
        total_reviewed = 0

        # Process in small batches for reliable JSON output
        for batch_start in range(0, min(len(convs), 30), BATCH_SIZE):
            batch = convs[batch_start:batch_start + BATCH_SIZE]
            batch_result = self._review_batch(batch, days)
            if "error" in batch_result:
                continue
            all_problems.extend(batch_result.get("problems_found", []))
            all_suggestions.extend(batch_result.get("suggestions", []))
            total_score += batch_result.get("quality_score", 0)
            total_reviewed += batch_result.get("reviewed", 0)

            # Store results for this batch
            for c in batch:
                review = ReviewResult(
                    conversation_id=c.id,
                    problems_found=json.dumps(batch_result.get("problems_found", []), ensure_ascii=False),
                    suggestions=json.dumps(batch_result.get("suggestions", []), ensure_ascii=False),
                    quality_score=batch_result.get("quality_score", 5),
                )
                db.add(review)
            db.commit()

        if total_reviewed == 0:
            return {"reviewed": 0, "problems_found": [], "suggestions": [],
                    "error": "所有批次审核失败，请检查LLM配置或稍后重试"}

        avg_score = total_score // total_reviewed if total_reviewed > 0 else 5
        return {
            "reviewed": total_reviewed,
            "quality_score": avg_score,
            "problems_found": all_problems,
            "suggestions": all_suggestions,
        }

    def _review_batch(self, convs, days: int) -> dict:
        conv_texts = []
        for i, c in enumerate(convs):
            msgs = json.loads(c.messages_history) if c.messages_history else []
            stages = json.loads(c.stage_history) if c.stage_history else []
            summary = f"对话{i + 1} (ID={c.id}, 阶段: {'→'.join(stages or [c.stage or 'unknown'])})\n"
            for m in msgs[-6:]:
                role = "顾客" if m.get("role") == "user" else "AI"
                summary += f"  {role}: {m.get('content', '')[:200]}\n"
            conv_texts.append(summary)

        prompt = f"以下是近{days}天的{len(conv_texts)}条对话，请审核：\n\n" + "\n---\n".join(conv_texts)

        try:
            resp = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=2048,
                system=REVIEW_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    text = block.text
                    break
            if not text:
                return {"reviewed": 0, "error": "LLM returned empty response"}

            result = self._parse_json(text)
            if result is None:
                return {"reviewed": 0, "error": f"JSON解析失败: {text[:200]}"}

            result["reviewed"] = len(convs)
            return result

        except Exception as e:
            return {"reviewed": 0, "error": str(e)[:200]}

    def _parse_json(self, text: str) -> dict | None:
        """Robust JSON parsing with multiple recovery strategies."""
        # Strategy 1: Strip markdown code blocks
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        # Strategy 2: Clean control characters
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)

        # Strategy 3: Try direct parse
        try:
            return self._normalize(json.loads(cleaned))
        except json.JSONDecodeError:
            pass

        # Strategy 4: Try to extract JSON between outermost braces
        m = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if m:
            try:
                return self._normalize(json.loads(m.group(0)))
            except json.JSONDecodeError:
                pass

        # Strategy 5: Fix common JSON issues and retry
        fixed = self._fix_json(cleaned)
        if fixed:
            try:
                return self._normalize(json.loads(fixed))
            except json.JSONDecodeError:
                pass

        # Strategy 6: Regex extract individual fields
        return self._extract_fallback(cleaned)

    def _fix_json(self, text: str) -> str | None:
        """Attempt to fix common JSON formatting errors from LLMs."""
        # Remove trailing commas before } or ]
        fixed = re.sub(r',(\s*[}\]])', r'\1', text)
        if fixed != text:
            return fixed
        return None

    def _normalize(self, data: dict) -> dict:
        """Normalize the LLM response structure to match expected format."""
        problems = data.get("problems", [])
        suggestions = data.get("suggestions", [])

        # Normalize problems: strings become objects
        normalized_problems = []
        for p in problems:
            if isinstance(p, str):
                normalized_problems.append({
                    "severity": "medium",
                    "category": "流程",
                    "description": p,
                    "conversation_index": 0,
                })
            elif isinstance(p, dict):
                normalized_problems.append({
                    "severity": p.get("severity", "medium"),
                    "category": p.get("category", "流程"),
                    "description": str(p.get("description", p.get("问题", ""))),
                    "conversation_index": p.get("conversation_index", 0),
                })

        # Normalize suggestions: strings become objects
        normalized_suggestions = []
        for s in suggestions:
            if isinstance(s, str):
                normalized_suggestions.append({
                    "category": "话术",
                    "description": s,
                })
            elif isinstance(s, dict):
                normalized_suggestions.append({
                    "category": s.get("category", "话术"),
                    "description": str(s.get("description", s.get("建议", ""))),
                })

        score = data.get("quality_score", 5)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            score = 5

        return {
            "problems_found": normalized_problems,
            "suggestions": normalized_suggestions,
            "quality_score": int(score),
        }

    def _extract_fallback(self, text: str) -> dict | None:
        """Regex-based fallback to extract key fields from malformed JSON."""
        result = {"problems_found": [], "suggestions": [], "quality_score": 5}

        # Extract quality_score
        score_m = re.search(r'"quality_score"\s*:\s*(\d+)', text)
        if score_m:
            score = int(score_m.group(1))
            if 1 <= score <= 10:
                result["quality_score"] = score

        # Extract problem descriptions
        for m in re.finditer(r'"description"\s*:\s*"([^"]{5,200})"', text):
            result["problems_found"].append({
                "severity": "medium",
                "category": "流程",
                "description": m.group(1),
                "conversation_index": 0,
            })

        # Extract suggestion descriptions
        for m in re.finditer(r'"description"\s*:\s*"([^"]{5,200})"', text):
            result["suggestions"].append({
                "category": "话术",
                "description": m.group(1),
            })
        # Deduplicate suggestions extracted as both problems and suggestions
        result["suggestions"] = [
            s for s in result["suggestions"]
            if s["description"] not in {p["description"] for p in result["problems_found"]}
        ]

        return result if (result["problems_found"] or result["suggestions"]) else None

    # ── Per-conversation review ──────────────────────────────────────────

    def review_single_conversation(self, db, conversation_id: int) -> dict | None:
        """Review a single conversation. Returns review dict or None."""
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv or not conv.messages_history:
            return None

        result = self._review_batch([conv], days=1)
        if "error" in result:
            return None
        return result
