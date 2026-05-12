# 焙草集AI销售助手——实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建药食同源门店AI对话推荐系统——微信小程序C端+员工端+后台管理端。

**Architecture:** FastAPI后端 + 状态机驱动的LLM对话引擎 + 规则+标签匹配的推荐引擎；微信原生小程序前端；Vue3后台。有赞承载订单/支付/物流，本系统专注AI推荐和健康数据，通过有赞SDK跳转下单。三阶段交付，每阶段产出独立可工作的系统。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Redis, OpenAI兼容API, 微信小程序原生框架, 有赞小程序SDK, Vue 3 + Element Plus

---

## 阶段一：数据层 + 后端核心

### Task 1: 项目初始化

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: 创建项目目录结构**

```bash
mkdir -p backend/app/{models,services,api,rag}
mkdir -p backend/tests
```

- [ ] **Step 2: 编写pyproject.toml**

```toml
[project]
name = "beicaoji"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "redis>=5.0",
    "openai>=1.12",
    "pydantic>=2.6",
    "pydantic-settings>=2.1",
    "python-dotenv>=1.0",
    "openpyxl>=3.1",
    "python-jose[cryptography]>=3.3",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]
```

- [ ] **Step 3: 编写config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///beicaoji.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    secret_key: str = "change-me-in-production"
    wechat_appid: str = ""
    wechat_secret: str = ""
    youzan_client_id: str = ""
    youzan_client_secret: str = ""
    youzan_access_token: str = ""
    youzan_shop_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

- [ ] **Step 4: 编写main.py骨架**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="焙草集AI助手API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 编写.env.example**

```
DATABASE_URL=sqlite:///beicaoji.db
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
SECRET_KEY=change-me
WECHAT_APPID=
WECHAT_SECRET=
```

- [ ] **Step 6: 验证项目可启动**

```bash
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: initialize backend project structure"
```

---

### Task 2: 数据库模型与商品数据导入

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/product.py`
- Create: `backend/app/models/customer.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/services/data_importer.py`
- Create: `backend/tests/test_importer.py`

- [ ] **Step 1: 编写product模型**

```python
# backend/app/models/product.py
from sqlalchemy import Column, String, Integer, Float, Boolean, Text
from app.models import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku_id = Column(String(20), unique=True, nullable=False, index=True)
    youzan_item_id = Column(String(50))             # 有赞商品ID（用于跳转下单）
    youzan_item_url = Column(String(500))           # 有赞商品链接
    category = Column(String(20), nullable=False)   # biscuit/bread/tea/toy
    feature_tag = Column(String(50))                # 产品特色
    name = Column(String(100), nullable=False)      # 产品名称
    ingredients = Column(Text)                       # 核心成分
    scene_tags = Column(Text)                        # 核心场景标签，逗号分隔
    sales_script = Column(Text)                      # 销售话术
    contraindication_tags = Column(Text)             # 禁忌标签，逗号分隔
    price = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
```

- [ ] **Step 2: 编写customer模型**

```python
# backend/app/models/customer.py
from sqlalchemy import Column, String, Integer, Text, DateTime, func
from app.models import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    wechat_openid = Column(String(100), unique=True, index=True)
    nickname = Column(String(50))
    phone = Column(String(20))
    constitution = Column(String(20))        # 体质倾向结果
    constitution_detail = Column(Text)       # 体质详细描述(JSON)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 3: 编写conversation模型**

```python
# backend/app/models/conversation.py
from sqlalchemy import Column, String, Integer, Text, DateTime, func
from app.models import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, index=True)
    stage = Column(String(30))               # screening/constitution/scene/recommend/done
    messages = Column(Text)                   # JSON: [{role, content, stage, timestamp}]
    constitution_raw = Column(Text)           # 体质原始回答(JSON)
    scene_input = Column(Text)                # 场景原始输入
    screening_result = Column(String(20))     # cleared/blocked/downgraded
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 4: 编写data_importer.py——从Excel导入商品**

```python
# backend/app/services/data_importer.py
import openpyxl
from pathlib import Path
from app.models.product import Product

PRODUCT_DIR = Path("E:/VIBE/beicaoji/beicaoji-产品目录")
FILE_MAP = {"biscuit": "biscuit.xlsx", "bread": "bread.xlsx", "tea": "tea.xlsx", "toy": "toy.xlsx"}

def import_all(session):
    count = 0
    for category, filename in FILE_MAP.items():
        count += import_sheet(session, PRODUCT_DIR / filename, category)
    session.commit()
    return count

def import_sheet(session, filepath, category):
    wb = openpyxl.load_workbook(filepath)
    ws = wb[wb.sheetnames[0]]
    count = 0
    for row in list(ws.iter_rows(min_row=2, values_only=True)):
        if not row[0]:
            continue
        product = Product(
            sku_id=str(row[0]).strip(),
            category=category,
            feature_tag=str(row[1] or "").strip(),
            name=str(row[2] or "").strip(),
            ingredients=str(row[3] or "").strip(),
            scene_tags=str(row[4] or "").strip(),
            sales_script=str(row[5] or "").strip(),
            contraindication_tags=str(row[6] or "").strip(),
        )
        session.add(product)
        count += 1
    return count
```

- [ ] **Step 5: 编写导入脚本并执行**

```bash
cd backend && python -c "
from app.models import init_db, Session
from app.services.data_importer import import_all
init_db()
session = Session()
n = import_all(session)
print(f'Imported {n} products')
session.close()
"
```

- [ ] **Step 6: 编写测试验证导入**

```python
# backend/tests/test_importer.py
def test_import_all(test_db):
    from app.services.data_importer import import_all
    count = import_all(test_db)
    assert count > 80
    from app.models.product import Product
    products = test_db.query(Product).all()
    categories = set(p.category for p in products)
    assert categories == {"biscuit", "bread", "tea", "toy"}
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ backend/app/services/data_importer.py backend/tests/
git commit -m "feat: add database models and Excel data importer"
```

---

### Task 3: 商品知识库查询服务

**Files:**
- Create: `backend/app/services/product_service.py`
- Create: `backend/tests/test_product_service.py`

- [ ] **Step 1: 编写商品查询服务**

```python
# backend/app/services/product_service.py
from app.models.product import Product

class ProductService:
    def __init__(self, session):
        self.session = session

    def search(self, scene_tags=None, exclude_tags=None, categories=None, limit=20):
        q = self.session.query(Product).filter(Product.is_active == True)
        if categories:
            q = q.filter(Product.category.in_(categories))
        results = q.all()

        if scene_tags:
            results = [p for p in results if p.scene_tags and
                       any(t in p.scene_tags for t in scene_tags)]
        if exclude_tags:
            results = [p for p in results if p.contraindication_tags and
                       not any(t in p.contraindication_tags for t in exclude_tags)]

        return results[:limit]

    def get_by_sku(self, sku_id):
        return self.session.query(Product).filter(Product.sku_id == sku_id).first()

    def get_all_active(self, category=None):
        q = self.session.query(Product).filter(Product.is_active == True)
        if category:
            q = q.filter(Product.category == category)
        return q.all()
```

- [ ] **Step 2: 编写测试**

```python
# backend/tests/test_product_service.py
def test_search_by_scene(test_db):
    from app.services.product_service import ProductService
    svc = ProductService(test_db)
    results = svc.search(scene_tags=["睡眠", "安神"])
    assert len(results) > 0
    # 所有结果应包含睡眠或安神标签
    for r in results:
        assert "睡眠" in r.scene_tags or "安神" in r.scene_tags
```

- [ ] **Step 3: Commit**

---

### Task 4: AI对话引擎——状态机核心

**Files:**
- Create: `backend/app/services/dialogue_engine.py`
- Create: `backend/app/services/prompts.py`
- Create: `backend/tests/test_dialogue_engine.py`

- [ ] **Step 1: 编写状态机定义和prompt模板**

```python
# backend/app/services/prompts.py
SYSTEM_PROMPT = """你是焙草集的健康顾问，帮助顾客了解自己的体质偏颇并推荐合适的药食同源产品。
重要规则：
1. 绝不使用"诊断""治疗""治愈""病症"等医疗用语
2. 只用"偏XX体质""调理倾向""食养建议"等表述
3. 如果顾客描述的症状听起来严重，建议其先咨询医生
4. 语气温和、专业、有同理心"""

SCREENING_PROMPT = """现在需要进行一项安全确认。请问你目前是否属于以下情况（可多选）：
A. 怀孕或备孕中
B. 正在哺乳期
C. 有确诊的重大疾病（如肿瘤、严重肝肾疾病等）
D. 正在服用处方药
E. 以上都没有

请如实告知，这关系到推荐的产品是否适合你。"""

CONSTITUTION_QUESTIONS = [
    {
        "id": "cold_hot",
        "question": "你冬天手脚通常是偏凉还是偏暖？",
        "options": ["偏凉，冬天容易手脚冰凉", "偏暖，不怎么怕冷", "说不准，看情况"],
        "field": "temperature_tendency",
    },
    {
        "id": "heat_signs",
        "question": "你平时容易上火吗？比如口干、长痘、口腔溃疡这类？",
        "options": ["经常，动不动就上火", "偶尔，不算频繁", "几乎不"],
        "field": "heat_signs",
    },
    {
        "id": "qi_deficiency",
        "question": "你容易感到疲劳、说话声音偏低、不太想动吗？",
        "options": ["是，经常觉得累、不想说话", "还好，正常范围内", "不会，精力比较充沛"],
        "field": "qi_deficiency",
    },
    {
        "id": "damp_heat",
        "question": "你饭后容易腹胀吗？大便偏黏、不太成形？",
        "options": ["经常这样", "偶尔", "基本没有"],
        "field": "damp_heat",
    },
    {
        "id": "cold_hot_bias",
        "question": "和别人相比，你觉得自己更怕冷还是更怕热？",
        "options": ["明显怕冷，比别人穿得多", "明显怕热，容易出汗", "差不多，没有明显偏向"],
        "field": "cold_hot_bias",
    },
    {
        "id": "sleep_baseline",
        "question": "你平时的睡眠质量怎么样？",
        "options": ["不太好，经常入睡困难或容易醒", "一般，时好时坏", "挺好的，基本没问题"],
        "field": "sleep_baseline",
    },
]

SCENE_QUESTION = "除了身体状态，最近有没有什么特别困扰你的？比如睡不好、消化差、容易疲劳、皮肤状态不好、想调理体质等等？"

SCENE_FOLLOWUP = "了解。能再具体一点吗？比如{specifics}？"

SCREENING_BLOCKED_MSG = """感谢你的坦诚。为了你的安全，建议在使用任何药食同源产品前先咨询你的医生。
我可以为你展示我们的产品目录，但不会做个性化推荐。需要我展示产品目录吗？"""

SCREENING_DRUG_MSG = """了解。方便说一下你在服用哪类药物吗？
这样我可以帮你排除可能和药物有冲突的产品。如果不方便说也没关系，我建议你先咨询医生再使用我们的产品。"""
```

- [ ] **Step 2: 编写对话引擎核心**

```python
# backend/app/services/dialogue_engine.py
import json
from enum import Enum
from openai import OpenAI
from app.config import settings
from app.services.prompts import (
    SYSTEM_PROMPT, SCREENING_PROMPT, CONSTITUTION_QUESTIONS,
    SCENE_QUESTION, SCENE_FOLLOWUP,
    SCREENING_BLOCKED_MSG, SCREENING_DRUG_MSG,
)

class Stage(str, Enum):
    GREETING = "greeting"
    SCREENING = "screening"
    SCREENING_RESULT = "screening_result"
    INFO_COLLECT = "info_collect"
    CONSTITUTION = "constitution"
    SCENE = "scene"
    RECOMMEND = "recommend"
    REPORT = "report"
    DONE = "done"

class DialogueEngine:
    def __init__(self):
        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def get_bot_message(self, conversation_state: dict) -> dict:
        """根据对话状态返回AI的下一句话"""
        stage = conversation_state.get("stage", Stage.GREETING)
        constitution_answers = json.loads(conversation_state.get("constitution_raw", "{}"))

        if stage == Stage.GREETING:
            return self._greeting()

        elif stage == Stage.SCREENING:
            return self._screening()

        elif stage == Stage.CONSTITUTION:
            idx = conversation_state.get("constitution_index", 0)
            if idx < len(CONSTITUTION_QUESTIONS):
                q = CONSTITUTION_QUESTIONS[idx]
                options_text = "\n".join(f"  · {o}" for o in q["options"])
                return {"message": f"{q['question']}\n\n{options_text}", "stage": stage, "question_index": idx}
            else:
                return {"message": SCENE_QUESTION, "stage": Stage.SCENE}

        elif stage == Stage.SCENE:
            # 场景追问
            last_answer = conversation_state.get("scene_raw", "")
            if last_answer and not conversation_state.get("scene_followup_done"):
                return {"message": self._scene_followup(last_answer), "stage": stage}
            return {"message": "好的，我已经了解了你的情况，让我为你分析一下……", "stage": Stage.RECOMMEND}

        return {"message": "有什么我可以帮你的？", "stage": stage}

    def process_user_message(self, state: dict, user_input: str) -> dict:
        """处理用户输入，更新状态，返回AI回复"""
        user_input = user_input.strip()

        if state.get("stage") == Stage.SCREENING:
            return self._handle_screening(state, user_input)

        elif state.get("stage") == Stage.CONSTITUTION:
            return self._handle_constitution(state, user_input)

        elif state.get("stage") == Stage.SCENE:
            return self._handle_scene(state, user_input)

        return self.get_bot_message(state)

    def _greeting(self):
        return {
            "message": "你好！我是焙草集的健康顾问 🌿\n\n"
                       "我可以帮你了解自己的身体状态，推荐适合你的药食同源调理产品。\n"
                       "整个过程大约1分钟，先简单了解一下你的情况。准备好了吗？",
            "stage": Stage.GREETING,
        }

    def _screening(self):
        return {"message": SCREENING_PROMPT, "stage": Stage.SCREENING}

    def _handle_screening(self, state, user_input):
        lowered = user_input.lower()
        blocked_keywords = ["a", "b", "c", "怀孕", "备孕", "哺乳", "肿瘤", "癌症"]
        drug_keywords = ["d", "处方药"]

        is_blocked = any(k in lowered for k in blocked_keywords)
        is_drug = any(k in lowered for k in drug_keywords)

        if is_blocked:
            return {"message": SCREENING_BLOCKED_MSG, "stage": Stage.SCREENING_RESULT,
                    "screening_result": "blocked"}
        elif is_drug:
            return {"message": SCREENING_DRUG_MSG, "stage": Stage.SCREENING_RESULT,
                    "screening_result": "downgraded"}
        else:
            return {"message": "好的，那我们继续。方便告诉我怎么称呼你吗？",
                    "stage": Stage.INFO_COLLECT, "screening_result": "cleared"}

    def _handle_constitution(self, state, user_input):
        idx = state.get("constitution_index", 0)
        raw = json.loads(state.get("constitution_raw", "{}"))
        q = CONSTITUTION_QUESTIONS[idx]
        raw[q["field"]] = user_input
        idx += 1

        if idx >= len(CONSTITUTION_QUESTIONS):
            return {
                "message": SCENE_QUESTION,
                "stage": Stage.SCENE,
                "constitution_raw": json.dumps(raw, ensure_ascii=False),
                "constitution_index": idx,
            }
        else:
            next_q = CONSTITUTION_QUESTIONS[idx]
            options_text = "\n".join(f"  · {o}" for o in next_q["options"])
            return {
                "message": f"{next_q['question']}\n\n{options_text}",
                "stage": Stage.CONSTITUTION,
                "constitution_raw": json.dumps(raw, ensure_ascii=False),
                "constitution_index": idx,
            }

    def _handle_scene(self, state, user_input):
        if not state.get("scene_raw"):
            return {
                "message": "好的，我已经了解你的情况了，现在帮你分析适合你的产品……",
                "stage": Stage.RECOMMEND,
                "scene_raw": user_input,
            }
        return {
            "message": "好的，我已经了解你的情况了，现在帮你分析适合你的产品……",
            "stage": Stage.RECOMMEND,
            "scene_raw": state["scene_raw"],
            "scene_followup_done": True,
        }

    def _scene_followup(self, scene_input):
        lowered = scene_input
        if "睡" in lowered:
            return "是入睡困难，还是半夜容易醒、醒了就睡不着？"
        elif "消化" in lowered or "肠胃" in lowered or "胃" in lowered:
            return "主要是饭后胀气、反酸，还是大便不太规律？"
        elif "累" in lowered or "疲劳" in lowered:
            return "是一整天都累，还是下午特别明显？"
        return "能再具体描述一下吗？"
```

- [ ] **Step 3: 编写核心流程测试**

```python
# backend/tests/test_dialogue_engine.py
import json
from app.services.dialogue_engine import DialogueEngine, Stage

def test_greeting():
    engine = DialogueEngine()
    result = engine.get_bot_message({"stage": Stage.GREETING})
    assert "焙草集" in result["message"]
    assert result["stage"] == Stage.GREETING

def test_screening_cleared():
    engine = DialogueEngine()
    state = {"stage": Stage.SCREENING}
    result = engine.process_user_message(state, "E")
    assert result["stage"] == Stage.INFO_COLLECT
    assert result["screening_result"] == "cleared"

def test_screening_blocked_pregnancy():
    engine = DialogueEngine()
    state = {"stage": Stage.SCREENING}
    result = engine.process_user_message(state, "A 怀孕")
    assert result["screening_result"] == "blocked"

def test_constitution_flow():
    engine = DialogueEngine()
    state = {"stage": Stage.CONSTITUTION, "constitution_index": 0, "constitution_raw": "{}"}
    result = engine.process_user_message(state, "偏凉")
    assert result["stage"] == Stage.CONSTITUTION
    raw = json.loads(result["constitution_raw"])
    assert raw.get("temperature_tendency") == "偏凉"
    assert result.get("constitution_index") == 1
```

- [ ] **Step 4: 运行测试验证**

```bash
cd backend && pytest tests/test_dialogue_engine.py -v
```

- [ ] **Step 5: Commit**

---

### Task 5: 体质分析服务

**Files:**
- Create: `backend/app/services/constitution_analyzer.py`
- Create: `backend/tests/test_constitution_analyzer.py`

- [ ] **Step 1: 编写体质分析器**

```python
# backend/app/services/constitution_analyzer.py
import json

CONSTITUTION_RULES = {
    "气虚质": {
        "signals": {"qi_deficiency": ["是，经常觉得累、不想说话"],
                     "cold_hot": ["偏凉，冬天容易手脚冰凉"]},
        "description": "偏气虚体质。这种体质的人通常容易疲劳、气短懒言、精神不振，容易出虚汗。日常适合多食用健脾益气的食物。",
        "avoid_tags": ["清热", "泻下", "寒凉"],
        "prefer_tags": ["补气", "健脾", "温补"],
    },
    "阳虚质": {
        "signals": {"temperature_tendency": ["偏凉，冬天容易手脚冰凉"],
                     "cold_hot_bias": ["明显怕冷，比别人穿得多"]},
        "description": "偏阳虚体质。阳气不足，畏寒怕冷，手脚常年偏凉。适合温补阳气的食养方向。",
        "avoid_tags": ["清热", "寒凉", "泻下"],
        "prefer_tags": ["温补", "补阳", "补气"],
    },
    "阴虚质": {
        "signals": {"heat_signs": ["经常，动不动就上火"],
                     "cold_hot_bias": ["明显怕热，容易出汗"]},
        "description": "偏阴虚体质。体内津液不足，容易口干、手心热、盗汗。适合滋阴润燥的食养方向。",
        "avoid_tags": ["温补", "补阳", "辛热"],
        "prefer_tags": ["滋阴", "润燥", "清热"],
    },
    "湿热质": {
        "signals": {"damp_heat": ["经常这样"],
                     "heat_signs": ["经常，动不动就上火"]},
        "description": "偏湿热体质。体内湿气和热邪并存，常见口苦、大便黏滞、皮肤易出油。适合清热利湿的食养方向。",
        "avoid_tags": ["温补", "滋腻", "补气"],
        "prefer_tags": ["清热", "利湿", "健脾"],
    },
    "平和质": {
        "signals": {},
        "description": "体质比较平和，阴阳气血协调。继续保持健康的生活方式即可，也可以根据季节适当调理。",
        "avoid_tags": [],
        "prefer_tags": [],
    },
}

def analyze(constitution_raw: str) -> dict:
    """分析体质原始回答，返回体质倾向结果"""
    answers = json.loads(constitution_raw) if isinstance(constitution_raw, str) else constitution_raw
    scores = {}

    for ctype, rules in CONSTITUTION_RULES.items():
        score = 0
        for field, expected_answers in rules["signals"].items():
            user_answer = answers.get(field, "")
            if any(ea in user_answer for ea in expected_answers):
                score += 1
        scores[ctype] = score

    # 找最高分
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "平和质"

    result = CONSTITUTION_RULES[best]
    return {
        "constitution_type": best,
        "score": scores[best],
        "description": result["description"],
        "avoid_tags": result["avoid_tags"],
        "prefer_tags": result["prefer_tags"],
        "all_scores": scores,
    }
```

- [ ] **Step 2: 编写测试**

```python
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
```

- [ ] **Step 3: Commit**

---

### Task 6: 推荐引擎

**Files:**
- Create: `backend/app/services/recommend_engine.py`
- Create: `backend/tests/test_recommend_engine.py`

- [ ] **Step 1: 编写推荐引擎**

```python
# backend/app/services/recommend_engine.py
import random
from app.services.product_service import ProductService
from app.services.constitution_analyzer import analyze

SCENE_TAG_MAP = {
    "睡": ["睡眠", "安神", "助眠"],
    "消化": ["消食", "健脾", "肠胃"],
    "胃": ["消食", "健脾", "肠胃"],
    "累": ["补气", "抗疲劳", "精力"],
    "疲劳": ["补气", "抗疲劳", "精力"],
    "皮肤": ["养颜", "润肤"],
    "上火": ["清热", "降火"],
    "调理": ["补气", "健脾", "滋阴", "温补"],
}

class RecommendEngine:
    def __init__(self, product_service: ProductService):
        self.product_service = product_service

    def recommend(self, constitution_raw: str, scene_input: str) -> dict:
        constitution = analyze(constitution_raw)

        # 1. 场景→标签映射
        scene_tags = self._extract_scene_tags(scene_input)

        # 2. 体质→排除/偏好标签
        avoid_tags = constitution["avoid_tags"]
        prefer_tags = constitution["prefer_tags"]

        # 3. 第一层：场景匹配
        scene_matches = self.product_service.search(scene_tags=scene_tags + prefer_tags)

        # 4. 第二层：体质过滤
        safe_matches = [p for p in scene_matches
                        if not any(t in (p.contraindication_tags or "")
                                   for t in avoid_tags)]

        # 5. 组合套餐（跨品类，每组2-3个）
        bundle = self._build_bundle(safe_matches)

        return {
            "constitution": constitution,
            "scene_tags": scene_tags,
            "products": safe_matches[:6],
            "bundle": [{"name": p.name, "sku_id": p.sku_id, "category": p.category,
                         "ingredients": p.ingredients, "price": p.price} for p in bundle],
        }

    def _extract_scene_tags(self, scene_input):
        tags = []
        for keyword, mapped_tags in SCENE_TAG_MAP.items():
            if keyword in scene_input:
                tags.extend(mapped_tags)
        return list(set(tags)) if tags else ["调理"]

    def _build_bundle(self, products, size=3):
        """从匹配商品中选跨品类的组合"""
        if len(products) < 2:
            return products
        cats = {}
        for p in products:
            cats.setdefault(p.category, []).append(p)
        bundle = []
        for cat_products in cats.values():
            if len(bundle) < size:
                bundle.append(cat_products[0])
        return bundle[:size]
```

- [ ] **Step 2: 编写测试**

```python
# backend/tests/test_recommend_engine.py
from app.services.recommend_engine import RecommendEngine

def test_recommend_bundle_cross_category(test_db_with_products):
    from app.services.product_service import ProductService
    svc = ProductService(test_db_with_products)
    engine = RecommendEngine(svc)
    result = engine.recommend(
        '{"qi_deficiency": "是，经常觉得累、不想说话"}',
        "我最近总是睡不好，容易醒"
    )
    assert result["constitution"]["constitution_type"] is not None
    assert len(result["bundle"]) >= 1
    # 套餐内品类不应重复
    cats = [p.category for p in result["bundle"]]
    assert len(cats) == len(set(cats))
```

- [ ] **Step 3: Commit**

---

### Task 7: 对话API接口

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/deps.py`

- [ ] **Step 1: 编写依赖注入**

```python
# backend/app/api/deps.py
from app.models import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 编写对话API**

```python
# backend/app/api/chat.py
import json
import redis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.dialogue_engine import DialogueEngine
from app.services.product_service import ProductService
from app.services.recommend_engine import RecommendEngine
from app.services.constitution_analyzer import analyze
from app.api.deps import get_db
from app.config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])
engine = DialogueEngine()
r = redis.from_url(settings.redis_url)

class ChatRequest(BaseModel):
    session_id: str
    message: str = ""

class ChatResponse(BaseModel):
    message: str
    stage: str
    quick_replies: list[str] | None = None
    recommendation: dict | None = None

@router.post("/send", response_model=ChatResponse)
def send_message(req: ChatRequest, db=Depends(get_db)):
    # 获取或创建对话状态
    state_key = f"chat:{req.session_id}"
    state_raw = r.get(state_key)
    state = json.loads(state_raw) if state_raw else {"stage": "greeting"}

    # 首次进入
    if not req.message:
        result = engine.get_bot_message(state)
    else:
        result = engine.process_user_message(state, req.message)

    # 到达推荐阶段时触发推荐
    recommendation = None
    if result.get("stage") == "recommend":
        product_svc = ProductService(db)
        rec_engine = RecommendEngine(product_svc)
        recommendation = rec_engine.recommend(
            state.get("constitution_raw", "{}"),
            result.get("scene_raw", "")
        )

    # 更新状态
    new_state = {**state, **result}
    r.set(state_key, json.dumps(new_state, ensure_ascii=False), ex=3600)

    return ChatResponse(
        message=result.get("message", ""),
        stage=result.get("stage", "greeting"),
        recommendation=recommendation,
    )

@router.post("/reset")
def reset_session(session_id: str):
    r.delete(f"chat:{session_id}")
    return {"status": "ok"}
```

- [ ] **Step 3: 注册路由到main.py**

在 `backend/app/main.py` 中添加：
```python
from app.api.chat import router as chat_router
app.include_router(chat_router)
```

- [ ] **Step 4: 用curl测试API**

```bash
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test1", "message": ""}'
```

- [ ] **Step 5: Commit**

---

### Task 8: 健康报告生成服务

**Files:**
- Create: `backend/app/services/report_generator.py`
- Create: `backend/tests/test_report_generator.py`

- [ ] **Step 1: 编写报告生成器**

```python
# backend/app/services/report_generator.py
from app.services.constitution_analyzer import analyze

LIFESTYLE_TIPS = {
    "气虚质": "日常可适当快走、八段锦等温和运动，不宜大汗淋漓。作息规律，避免熬夜耗气。",
    "阳虚质": "适合晨练、太极拳，多晒太阳。饮食宜温热，少食生冷。",
    "阴虚质": "避免剧烈运动和高温环境，可练习瑜伽、冥想。少熬夜，多补充水分。",
    "湿热质": "适合中等强度运动如慢跑、游泳，出汗有助于排湿。少吃油腻甜腻食物。",
    "平和质": "保持现状即可。四季饮食顺应时节，劳逸结合。",
}

FOOD_TIPS = {
    "气虚质": "适合：山药、红枣、莲子、小米、牛肉、鸡肉等健脾益气的食材。",
    "阳虚质": "适合：羊肉、韭菜、核桃、桂圆、生姜等温补阳气的食材。",
    "阴虚质": "适合：银耳、百合、梨、鸭肉、枸杞等滋阴润燥的食材。",
    "湿热质": "适合：薏米、绿豆、冬瓜、苦瓜、赤小豆等清热利湿的食材。",
    "平和质": "均衡饮食，各种食材都可适量摄入。",
}

def generate_report(constitution_raw: str, scene_input: str, recommendation: dict,
                    customer_name: str = "") -> dict:
    const = analyze(constitution_raw)
    ctype = const["constitution_type"]

    return {
        "customer_name": customer_name,
        "constitution_type": ctype,
        "constitution_desc": const["description"],
        "food_advice": FOOD_TIPS.get(ctype, FOOD_TIPS["平和质"]),
        "lifestyle_advice": LIFESTYLE_TIPS.get(ctype, LIFESTYLE_TIPS["平和质"]),
        "scene_concern": scene_input,
        "bundle": [
            {
                "name": p.name,
                "ingredients": p.ingredients,
                "reason": f"此产品含有{p.ingredients}，适合偏{ctype}且关注{scene_input}的你。",
                "price": p.price or 0,
            }
            for p in recommendation.get("bundle", [])
        ],
        "disclaimer": "本报告基于传统食养理念，仅为调理建议参考，不构成医疗诊断。如有健康问题请咨询执业医师。",
    }
```

- [ ] **Step 2: 编写测试**

```python
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
```

- [ ] **Step 3: 将报告生成接入chat API**

在 `/api/chat/send` 接口中，推荐阶段同时生成报告：
```python
from app.services.report_generator import generate_report
# ...
report = generate_report(
    state.get("constitution_raw", "{}"),
    result.get("scene_raw", ""),
    recommendation,
    state.get("customer_name", "")
)
```

- [ ] **Step 4: Commit**

---

## 阶段二：微信小程序

### Task 9: 小程序项目初始化

**Files:**
- Create: `miniprogram/app.json`
- Create: `miniprogram/app.js`
- Create: `miniprogram/app.wxss`
- Create: `miniprogram/pages/chat/chat.js`
- Create: `miniprogram/pages/chat/chat.wxml`
- Create: `miniprogram/pages/chat/chat.wxss`
- Create: `miniprogram/pages/report/report.js`
- Create: `miniprogram/pages/report/report.wxml`
- Create: `miniprogram/pages/report/report.wxss`
- Create: `miniprogram/utils/api.js`

- [ ] **Step 1: app.json配置**

```json
{
  "pages": [
    "pages/chat/chat",
    "pages/report/report",
    "pages/order/order",
    "pages/staff/customers",
    "pages/staff/detail"
  ],
  "window": {
    "navigationBarTitleText": "焙草集",
    "navigationBarBackgroundColor": "#5B8C5A",
    "navigationBarTextStyle": "white"
  }
}
```

- [ ] **Step 2: API工具封装**

```javascript
// miniprogram/utils/api.js
const BASE = 'https://your-server.com/api';

function generateSessionId() {
  let sid = wx.getStorageSync('session_id');
  if (!sid) {
    sid = 'wx_' + Date.now() + '_' + Math.random().toString(36).slice(2);
    wx.setStorageSync('session_id', sid);
  }
  return sid;
}

function sendMessage(message = '') {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE + '/chat/send',
      method: 'POST',
      data: { session_id: generateSessionId(), message },
      success: res => resolve(res.data),
      fail: reject
    });
  });
}

module.exports = { sendMessage, BASE };
```

- [ ] **Step 3: Chat页面——消息列表和输入框**

```html
<!-- miniprogram/pages/chat/chat.wxml -->
<view class="chat-container">
  <scroll-view class="message-list" scroll-y scroll-into-view="msg-{{messages.length - 1}}">
    <view wx:for="{{messages}}" wx:key="index" id="msg-{{index}}"
          class="message {{item.role}}">
      <view class="bubble">{{item.content}}</view>
    </view>
    <view wx:if="{{loading}}" class="message bot">
      <view class="bubble typing">...</view>
    </view>
  </scroll-view>

  <view class="input-bar">
    <input class="input" placeholder="输入你的情况..."
           value="{{inputText}}" bindinput="onInput" confirm-type="send"
           bindconfirm="onSend"/>
    <button class="send-btn" bindtap="onSend">发送</button>
  </view>
</view>
```

- [ ] **Step 4: Chat页面JS逻辑**

```javascript
// miniprogram/pages/chat/chat.js
const api = require('../../utils/api');

Page({
  data: { messages: [], inputText: '', loading: false },

  onLoad() {
    this.addMessage('bot', '你好！我是焙草集的健康顾问，可以帮你找到最适合你的调理方案。准备好了就告诉我～');
  },

  addMessage(role, content) {
    this.data.messages.push({ role, content });
    this.setData({ messages: this.data.messages });
  },

  onInput(e) { this.setData({ inputText: e.detail.value }); },

  async onSend() {
    const text = this.data.inputText.trim();
    if (!text) return;
    this.addMessage('user', text);
    this.setData({ inputText: '', loading: true });

    const res = await api.sendMessage(text);
    this.setData({ loading: false });
    this.addMessage('bot', res.message);

    if (res.recommendation) {
      wx.navigateTo({
        url: '/pages/report/report',
        success: page => page.setData({ report: res.recommendation })
      });
    }
  }
});
```

- [ ] **Step 5: Commit**

---

### Task 10: 健康报告页面 + 购买引导

**Files:**
- Create: `miniprogram/pages/report/report.js`
- Create: `miniprogram/pages/report/report.wxml`

- [ ] **Step 1: 报告页面**

```html
<!-- miniprogram/pages/report/report.wxml -->
<view class="report-page">
  <view class="report-header">
    <text class="title">你的调理建议报告</text>
    <text class="subtitle">基于传统食养理念 · 仅供参考</text>
  </view>

  <view class="section">
    <text class="section-title">体质倾向</text>
    <text class="section-body">{{report.constitution_desc}}</text>
  </view>

  <view class="section">
    <text class="section-title">食养方向</text>
    <text class="section-body">{{report.food_advice}}</text>
  </view>

  <view class="section">
    <text class="section-title">生活小贴士</text>
    <text class="section-body">{{report.lifestyle_advice}}</text>
  </view>

  <view class="section">
    <text class="section-title">推荐商品</text>
    <view wx:for="{{report.bundle}}" wx:key="name" class="product-card">
      <text class="product-name">{{item.name}}</text>
      <text class="product-ingredients">成分：{{item.ingredients}}</text>
      <text class="product-reason">{{item.reason}}</text>
      <text class="product-price">¥{{item.price}}</text>
    </view>
  </view>

  <view class="actions">
    <button class="btn-primary" bindtap="onBuyOffline">到店出示此页购买</button>
  </view>

  <view class="disclaimer">
    <text>{{report.disclaimer}}</text>
  </view>
</view>
```

- [ ] **Step 2: 报告页面JS**

```javascript
// miniprogram/pages/report/report.js
Page({
  data: { report: {} },

  onBuyOffline() {
    wx.showModal({
      title: '到店购买',
      content: '请向店员出示此推荐页面，店员会帮你完成购买。',
      showCancel: false,
    });
  }
});
```

- [ ] **Step 2: Commit**

---

## 阶段三：员工端 + 后台管理

### Task 11: 员工端——顾客列表与详情

**Files:**
- Create: `miniprogram/pages/staff/customers.js`
- Create: `miniprogram/pages/staff/customers.wxml`
- Create: `miniprogram/pages/staff/detail.js`
- Create: `miniprogram/pages/staff/detail.wxml`
- Create: `backend/app/api/staff.py`

- [ ] **Step 1: 后端员工API**

```python
# backend/app/api/staff.py
from fastapi import APIRouter, Depends
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.api.deps import get_db

router = APIRouter(prefix="/api/staff", tags=["staff"])

@router.get("/customers")
def list_customers(page: int = 1, page_size: int = 20, db=Depends(get_db)):
    offset = (page - 1) * page_size
    customers = db.query(Customer).order_by(Customer.created_at.desc()).offset(offset).limit(page_size).all()
    return {"customers": [
        {"id": c.id, "nickname": c.nickname, "phone": c.phone,
         "constitution": c.constitution, "created_at": str(c.created_at)}
        for c in customers
    ]}

@router.get("/customers/{customer_id}")
def customer_detail(customer_id: int, db=Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    conversations = db.query(Conversation).filter(Conversation.customer_id == customer_id).all()
    return {"customer": customer, "conversations": conversations}
```

- [ ] **Step 2: 员工端小程序页面（顾客列表 + 详情）**

与普通用户相同的页面结构，增加店员入口（通过微信openid判断角色）。

- [ ] **Step 3: Commit**

---

### Task 12: 后台管理端

**Files:**
- Create: `admin/` (Vue 3 + Element Plus项目)
- Create: `backend/app/api/admin.py`

- [ ] **Step 1: 后台API——增加有赞商品关联**

```python
# backend/app/api/admin.py
from fastapi import APIRouter, Depends
from app.models.product import Product
from app.models.customer import Customer
from app.api.deps import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def stats(db=Depends(get_db)):
    products_count = db.query(Product).filter(Product.is_active == True).count()
    customers_count = db.query(Customer).count()
    with_tags = db.query(Product).filter(
        Product.is_active == True, Product.scene_tags != ""
    ).count()
    return {
        "products_count": products_count,
        "customers_count": customers_count,
        "tag_completion_rate": round(with_tags / products_count * 100, 1) if products_count else 0,
    }

@router.put("/products/{product_id}")
def update_product(product_id: int, data: dict, db=Depends(get_db)):
    """更新商品标签、品类、价格等"""
    allowed = ["scene_tags", "contraindication_tags", "category",
               "feature_tag", "price", "is_active"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    db.query(Product).filter(Product.id == product_id).update(update_data)
    db.commit()
    return {"status": "ok"}
```

- [ ] **Step 2: 后台前端框架**

使用Vue 3 + Element Plus，包含页面：
- 仪表盘（统计概览、标签完善率）
- 商品管理（列表、编辑体质/场景/禁忌标签、品类、上下架）
- 顾客管理（搜索、查看对话历史、报告）

- [ ] **Step 3: Commit**

---

---

## 阶段四：有赞对接（可延迟，有赞API需付费）

> 此阶段待有赞API开通后再执行。当前MVP阶段，推荐结果引导顾客到店购买即可。

### Task 13: 有赞商品同步与下单跳转

**Files:**
- Create: `backend/app/services/youzan_sync.py`
- Modify: `backend/app/services/recommend_engine.py`
- Modify: `miniprogram/pages/report/report.wxml`
- Modify: `miniprogram/pages/report/report.js`

- [ ] **Step 1: 编写有赞商品同步服务** (同之前Task 3内容)
- [ ] **Step 2: 推荐结果附加有赞跳转链接**
- [ ] **Step 3: 小程序报告页增加有赞SDK跳转**
- [ ] **Step 4: 后台增加有赞同步按钮和关联管理**

---

## 执行说明

阶段一可以独立完成并测试（有完整后端API），阶段二依赖阶段一，阶段三依赖阶段二的数据模型。建议按顺序执行。阶段四待有赞API开通后再做。

执行时每个Task内部按step顺序，每完成一个step检查结果，完成整个Task后commit。
