"""独立报告页面 —— 生成精美HTML调理报告"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.services.constitution_analyzer import analyze
from app.services.report_generator import generate_report
from app.api.deps import get_db

router = APIRouter(prefix="/api/report", tags=["report"])

# In-memory session store reference (shared with chat.py via app state)
from app.api.chat import _session_store

REPORT_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: -apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif;
  background: #f5f5f0;
  color: #3d3d3d;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  max-width: 480px;
  margin: 0 auto;
  padding: 0 0 40px 0;
}
.hero {
  background: linear-gradient(135deg, #5B8C5A 0%, #7CB342 100%);
  color: white;
  text-align: center;
  padding: 48px 24px 36px;
  position: relative;
  overflow: hidden;
}
.hero::after {
  content: '';
  position: absolute;
  bottom: -20px; left: -20px; right: -20px;
  height: 40px;
  background: #f5f5f0;
  border-radius: 50% 50% 0 0;
}
.hero .icon { font-size: 48px; margin-bottom: 12px; }
.hero h1 { font-size: 24px; font-weight: 700; letter-spacing: 1px; margin-bottom: 6px; }
.hero .greeting { font-size: 15px; opacity: 0.9; margin-top: 4px; }
.hero .date { font-size: 12px; opacity: 0.7; margin-top: 8px; }

.card {
  background: white;
  border-radius: 16px;
  padding: 24px 20px;
  margin: 16px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.card-title {
  font-size: 17px;
  font-weight: 700;
  color: #5B8C5A;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title .dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #5B8C5A;
  flex-shrink: 0;
}
.card-body { font-size: 14px; color: #666; }

.constitution-badge {
  display: inline-block;
  background: #e8f5e9;
  color: #5B8C5A;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f0;
}
.product-item:last-child { border-bottom: none; }
.product-emoji {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}
.product-emoji.biscuit { background: #fff3e0; }
.product-emoji.bread { background: #fce4ec; }
.product-emoji.tea { background: #e0f2f1; }
.product-emoji.toy { background: #f3e5f5; }
.product-info { flex:1; min-width:0; }
.product-info .p-name { font-size: 15px; font-weight: 600; color: #333; }
.product-info .p-desc { font-size: 12px; color: #999; margin-top: 2px; }
.product-info .p-reason {
  font-size: 12px; color: #5B8C5A; margin-top: 4px;
  background: #e8f5e9; padding: 4px 8px; border-radius: 6px;
  display: inline-block;
}
.product-price { font-weight: 700; color: #e6a23c; font-size: 16px; flex-shrink: 0; }

.tips-list { list-style: none; }
.tips-list li {
  padding: 8px 0 8px 20px;
  position: relative;
  font-size: 14px;
  color: #666;
}
.tips-list li::before {
  content: '';
  position: absolute;
  left: 0; top: 16px;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #5B8C5A;
}

.divider { text-align:center; margin:24px 0; color:#ccc; font-size:12px; letter-spacing:2px; }

.footer {
  text-align: center;
  padding: 24px 16px;
  color: #999;
  font-size: 12px;
}

.btn-fixed {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #5B8C5A;
  color: white;
  border: none;
  padding: 14px 48px;
  border-radius: 28px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(91,140,90,0.3);
  cursor: pointer;
  z-index: 100;
}
.btn-fixed:active { opacity: 0.9; transform: translateX(-50%) scale(0.98); }
"""

CATEGORY_EMOJI = {"biscuit": "🍪", "bread": "🍞", "tea": "🍵", "toy": "🎐"}


@router.get("/{session_id}", response_class=HTMLResponse)
def view_report(session_id: str, db=Depends(get_db)):
    state_key = f"chat:{session_id}"
    state_raw = _session_store.get(state_key)
    if not state_raw or not state_raw.get("constitution_raw"):
        return HTMLResponse(
            "<html><body style='text-align:center;padding:60px 20px;font-family:sans-serif'>"
            "<h2>报告未找到</h2><p>会话已过期或未完成对话流程。请回到聊天页面重新开始。</p>"
            "</body></html>"
        )

    state = state_raw
    report = generate_report(
        state.get("constitution_raw", "{}"),
        state.get("scene_raw", ""),
        state.get("recommendation", {}),
        state.get("customer_name", ""),
    )

    from datetime import datetime
    today = datetime.now().strftime("%Y年%m月%d日")
    name = report.get("customer_name", "顾客")
    greeting = f"{name}，你好呀" if name else "你好呀"

    products_html = ""
    for p in report.get("bundle", []):
        cat = p.get("category", "biscuit")
        emoji = CATEGORY_EMOJI.get(cat, "🌿")
        price = f"¥{p['price']:.0f}" if p.get("price") else "到店询价"
        products_html += f"""
        <div class="product-item">
          <div class="product-emoji {cat}">{emoji}</div>
          <div class="product-info">
            <div class="p-name">{p['name']}</div>
            <div class="p-desc">成分：{p.get('ingredients', '药食同源食材')}</div>
            <div class="p-reason">{p.get('reason', '适合你的体质调理')}</div>
          </div>
          <div class="product-price">{price}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>焙草集 · 个人调理报告</title>
<style>{REPORT_CSS}</style>
</head>
<body>

<div class="hero">
  <div class="icon">🌿</div>
  <h1>个人调理报告</h1>
  <div class="greeting">{greeting}</div>
  <div class="date">{today}</div>
</div>

<div class="card">
  <div class="card-title"><span class="dot"></span>体质倾向</div>
  <div class="constitution-badge">{report['constitution_type']}</div>
  <div class="card-body">{report['constitution_desc']}</div>
</div>

<div class="card">
  <div class="card-title"><span class="dot"></span>食养建议</div>
  <div class="card-body">{report['food_advice']}</div>
</div>

<div class="card">
  <div class="card-title"><span class="dot"></span>生活小贴士</div>
  <div class="card-body">{report['lifestyle_advice']}</div>
</div>

<div class="divider">· · ·</div>

<div class="card">
  <div class="card-title"><span class="dot"></span>为你推荐</div>
  {products_html}
</div>

<div class="footer">
  <p>基于传统食养理念 · 仅供参考</p>
  <p style="margin-top:4px">本报告不构成医疗诊断，如有健康问题请咨询执业医师</p>
</div>

<button class="btn-fixed" onclick="window.close()">返回对话</button>

</body>
</html>"""

    return HTMLResponse(html)
