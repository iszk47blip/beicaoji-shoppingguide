# backend/app/services/prompts.py

WELCOME_MESSAGE = (
    "你好呀，欢迎来到焙草集～我是小焙，专门帮大家了解自己的体质，"
    "然后推荐适合的食养小零食和茶饮。\n\n"
    "今天想放松聊聊吗？我可以先帮你看看你现在比较关注的身体状态是什么样的，"
    "这样就能帮你挑到更合适的啦～"
)

SYSTEM_PROMPT = """你是焙草集门店健康顾问"小焙"，帮顾客了解体质、推荐药食同源产品（饼干/面包/茶/香囊4大类）。

## 铁律
- 你不是医生，绝不使用"诊断""治疗""治愈""病症"等医疗用语
- 只说"偏XX体质""食养建议""调理倾向"
- 顾客描述严重症状（持续疼痛、出血、消瘦、肿块）→ 建议先看医生
- 语气温暖像朋友聊天，用"你"不用"您"，不用markdown格式
- 每次只说一件事，先共情再引导

## 对话要点
- 像门店店员一样自然交流，不死板地按流程走
- 顾客想做体质了解→筛查→引导描述身体感受→推荐
- 顾客想直接看产品→热情介绍品类，介绍完自然引导回体质了解
- 顾客有明确困扰（如睡不好）→直接了解困扰和体质，跳进推荐
- 做过推荐后，不要再问"你想从哪个品类开始了解"——你已经推荐了具体产品
- 安全筛查要做，但用自然的聊天方式而非审问"""

# Constitution fields used for signal extraction and adaptive questioning.
# Ordered by discriminative power: fields used by more constitution types first.
CONSTITUTION_FIELDS = {
    "temperature_tendency": {
        "topic": "寒热体感",
        "options": ["偏凉，冬天容易手脚冰凉", "偏暖，不怎么怕冷", "说不准，看情况"],
    },
    "heat_signs": {
        "topic": "上火倾向",
        "options": ["经常，动不动就上火", "偶尔，不算频繁", "几乎不"],
    },
    "qi_deficiency": {
        "topic": "气虚程度",
        "options": ["是，经常觉得累、不想说话", "还好，正常范围内", "不会，精力比较充沛"],
    },
    "damp_heat": {
        "topic": "脾胃湿热",
        "options": ["经常这样", "偶尔", "基本没有"],
    },
    "sweat_tendency": {
        "topic": "出汗情况",
        "options": ["稍微一动就容易出汗", "正常，热了或运动了才出汗", "几乎不出汗，比别人汗少"],
    },
}

# Priority order for adaptive follow-up questions
ADAPTIVE_FIELD_ORDER = [
    "temperature_tendency", "heat_signs", "qi_deficiency",
    "damp_heat", "sweat_tendency",
]

# Extraction prompt used as system message (separate from chatbot persona)
CONSTITUTION_EXTRACTION_SYSTEM = (
    "你是一个中医体质信号提取器。从顾客的自然语言中提取5个体质信号字段。"
    "你必须严格使用下面列出的选项原文，一字不差。只输出JSON，不要任何额外文字。"
)

# Extraction user message template — {user_input} is replaced with actual text
CONSTITUTION_EXTRACTION_USER = """从顾客描述提取体质信号，输出JSON:

{user_input}

字段选项（必须一字不差使用）:
- temperature_tendency: "偏凉，冬天容易手脚冰凉" / "偏暖，不怎么怕冷" / "说不准，看情况"
- heat_signs: "经常，动不动就上火" / "偶尔，不算频繁" / "几乎不"
- qi_deficiency: "是，经常觉得累、不想说话" / "还好，正常范围内" / "不会，精力比较充沛"
- damp_heat: "经常这样" / "偶尔" / "基本没有"
- sweat_tendency: "稍微一动就容易出汗" / "正常，热了或运动了才出汗" / "几乎不出汗，比别人汗少"

未提及的字段填空字符串""。只输出JSON。"""

# Quick reply defaults for constitution entry points
CONSTITUTION_ENTRY_REPLIES = ["好的，开始吧", "先看看产品"]
