"""独立报告页面 —— 生成精美HTML调理报告"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.services.constitution_analyzer import analyze
from app.services.report_generator import generate_report
from app.api.deps import get_db

router = APIRouter(prefix="/api/report", tags=["report"])

from app.api.chat import _session_store

REPORT_CSS = """
:root {
  --ink: #3d3226;
  --ink-light: #6b5f52;
  --paper: #faf7f2;
  --paper-dark: #f0ebe0;
  --accent: #8B4513;
  --accent-soft: #c4a882;
  --jade: #7a9a7e;
  --jade-light: #e8efe9;
  --red-seal: #c0392b;
  --border: #e0d8cc;
  --shadow: 0 2px 16px rgba(61,50,38,0.06);
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: "PingFang SC","Noto Serif SC","STSong",serif;
  background: #e8e0d5;
  color: var(--ink);
  line-height: 1.8;
  -webkit-font-smoothing: antialiased;
  max-width: 480px;
  margin: 0 auto;
  padding: 0 0 60px 0;
}

/* ---- Hero / Cover ---- */
.hero {
  background: linear-gradient(165deg, #5a4a3a 0%, #3d3226 40%, #2c2418 100%);
  color: #f5efe5;
  text-align: center;
  padding: 56px 28px 44px;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 5 L55 30 L30 55 L5 30Z' fill='none' stroke='rgba(255,255,255,0.04)' stroke-width='1'/%3E%3C/svg%3E") repeat;
  opacity: 0.5;
}
.hero > * { position: relative; z-index: 1; }
.hero .seal {
  width: 56px; height: 56px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  font-size: 26px;
}
.hero h1 {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 3px;
  margin-bottom: 6px;
}
.hero .subtitle {
  font-size: 12px;
  opacity: 0.6;
  letter-spacing: 2px;
}
.hero .date {
  font-size: 11px;
  opacity: 0.45;
  margin-top: 12px;
  letter-spacing: 1px;
}
.hero .name {
  font-size: 18px;
  font-weight: 600;
  margin-top: 8px;
}

/* ---- Section Cards ---- */
.section {
  background: var(--paper);
  border-radius: 12px;
  padding: 28px 24px;
  margin: 14px 14px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  position: relative;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.section-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.section-icon.constitution { background: #f5ebe0; }
.section-icon.food       { background: #e8efe9; }
.section-icon.lifestyle  { background: #e8edf5; }
.section-icon.seasonal   { background: #f5f0e8; }
.section-icon.product    { background: #fdf2f0; }

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 1px;
}

/* ---- Constitution Badge ---- */
.constitution-badge {
  display: inline-block;
  background: linear-gradient(135deg, #5a4a3a, #8B4513);
  color: #faf7f2;
  padding: 6px 20px;
  border-radius: 20px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 2px;
  margin-bottom: 10px;
}
.constitution-desc {
  font-size: 14px;
  color: var(--ink-light);
  line-height: 1.8;
}

/* ---- Advice text ---- */
.advice-text {
  font-size: 14px;
  color: var(--ink-light);
  line-height: 1.9;
}

/* ---- Product Card ---- */
.product-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
}
.product-card:last-child { border-bottom: none; }
.product-emoji {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}
.product-emoji.biscuit { background: #faf0e0; }
.product-emoji.bread   { background: #fdf0ed; }
.product-emoji.tea     { background: #eaf5ed; }
.product-emoji.toy     { background: #f5eff8; }
.product-info { flex:1; min-width:0; }
.product-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 2px;
}
.product-ingredients {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}
.product-reason {
  font-size: 13px;
  color: var(--ink-light);
  line-height: 1.7;
}
.product-price {
  font-weight: 700;
  color: #c0392b;
  font-size: 17px;
  flex-shrink: 0;
  align-self: center;
}

/* ---- Divider ---- */
.divider {
  text-align: center;
  margin: 28px 0;
  color: var(--accent-soft);
  font-size: 11px;
  letter-spacing: 6px;
}

/* ---- Disclaimer ---- */
.disclaimer-box {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin: 14px 14px;
  text-align: center;
  font-size: 11px;
  color: #b5a898;
  line-height: 1.7;
}

/* ---- Footer ---- */
.footer {
  text-align: center;
  padding: 24px 16px 8px;
  color: #c5b8a8;
  font-size: 11px;
  letter-spacing: 1px;
}

/* ---- Back Button ---- */
.btn-back {
  display: block;
  width: calc(100% - 28px);
  margin: 20px 14px 0;
  padding: 14px;
  background: linear-gradient(135deg, #5a4a3a, #8B4513);
  color: #faf7f2;
  border: none;
  border-radius: 24px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 2px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(139,69,19,0.2);
}
.btn-back:active { opacity: 0.9; transform: scale(0.98); }

/* ---- Stepper ---- */
.stepper { display:flex; align-items:center; gap:6px; flex-shrink:0; }
.stepper-btn {
  width:28px; height:28px; border-radius:50%; border:1.5px solid #ccc;
  background:white; font-size:16px; font-weight:600; cursor:pointer;
  display:flex; align-items:center; justify-content:center; line-height:1; color:#666;
}
.stepper-btn.plus { background:var(--jade); border-color:var(--jade); color:white; }
.stepper-btn:disabled { opacity:0.3; cursor:default; pointer-events:none; }
.stepper-qty { min-width:22px; text-align:center; font-size:15px; font-weight:600; color:#333; }

/* ---- Cart bar ---- */
#cart-bar {
  display:none; position:fixed; bottom:0; left:50%; transform:translateX(-50%);
  width:100%; max-width:480px; background:#3d3226; color:#faf7f2;
  padding:14px 20px; z-index:50; cursor:pointer;
  align-items:center; justify-content:space-between;
  box-shadow:0 -4px 16px rgba(0,0,0,0.15);
}
#cart-bar.show { display:flex; animation:slideUp 0.3s ease; }
@keyframes slideUp { from { transform:translateX(-50%) translateY(100%); } to { transform:translateX(-50%) translateY(0); } }
#cart-bar .cart-icon { position:relative; font-size:20px; }
#cart-bar .cart-badge {
  position:absolute; top:-6px; right:-8px; min-width:18px; height:18px;
  border-radius:9px; background:#e74c3c; color:white; font-size:11px; font-weight:700;
  display:flex; align-items:center; justify-content:center; padding:0 4px;
}
#cart-bar .cart-total { font-size:17px; font-weight:700; }

/* ---- Order overlay ---- */
#order-overlay {
  display:none; position:fixed; top:0; left:0; right:0; bottom:0;
  background:rgba(0,0,0,0.5); z-index:100; justify-content:center; align-items:flex-end;
}
#order-overlay.show { display:flex; }
#order-modal {
  width:100%; max-width:480px; max-height:80vh; background:white;
  border-radius:20px 20px 0 0; overflow-y:auto; padding:24px 20px; animation:slideUp 0.3s ease;
}
#order-modal .order-check {
  width:56px; height:56px; border-radius:50%; background:#e8f5e9;
  display:flex; align-items:center; justify-content:center; font-size:28px; margin:0 auto 12px;
}
#order-modal .order-title { font-size:18px; font-weight:700; text-align:center; margin-bottom:4px; }
#order-modal .order-no { font-size:12px; color:#999; text-align:center; }
#order-modal .order-section { background:#faf7f2; border-radius:12px; padding:16px; margin-bottom:12px; }
#order-modal .order-item { display:flex; justify-content:space-between; padding:6px 0; font-size:14px; }
#order-modal .order-total-row {
  display:flex; justify-content:space-between; padding:10px 0 0;
  border-top:1px solid #e0d8cc; margin-top:8px; font-size:16px; font-weight:700;
}
#order-modal .order-actions { display:flex; gap:10px; margin-top:20px; }
#order-modal .btn-close { flex:1; padding:13px; background:#f5f5f5; border:none; border-radius:24px; font-size:15px; cursor:pointer; }
#order-modal .btn-confirm {
  flex:2; padding:13px; background:linear-gradient(135deg,#5B8C5A,#7CB342);
  color:white; border:none; border-radius:24px; font-size:15px; font-weight:600; cursor:pointer;
}

/* ---- Toast ---- */
#toast {
  position:fixed; top:80px; left:50%; transform:translateX(-50%) translateY(-20px);
  background:#3d3226; color:white; padding:10px 24px; border-radius:20px; font-size:14px;
  z-index:200; opacity:0; transition:all 0.3s; pointer-events:none;
}
#toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
"""

CATEGORY_EMOJI = {"biscuit": "🍪", "bread": "🍞", "tea": "🍵", "toy": "🎐"}


@router.get("/{session_id}/data")
def report_data(session_id: str):
    state_key = f"chat:{session_id}"
    state_raw = _session_store.get(state_key)
    if not state_raw:
        return {"error": "session not found"}
    rec = state_raw.get("recommendation")
    if not rec:
        return {"error": "no recommendation data"}
    return {"recommendation": rec}


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
    name = report.get("customer_name", "")

    # Build product cards with steppers
    products_html = ""
    for i, p in enumerate(report.get("bundle", [])):
        cat = p.get("category", "biscuit")
        emoji = CATEGORY_EMOJI.get(cat, "🌿")
        price_val = p.get("price", 0) or 0
        sku = p.get("sku_id", f"RPT-{i}")
        ingredients = p.get("ingredients", "精选药食同源食材")
        pdata = json.dumps({"sku_id":sku,"name":p.get("name",""),"price":price_val,"category":cat,"ingredients":ingredients}, ensure_ascii=False)
        products_html += f"""
        <div class="product-card rec-card" data-sku="{sku}" data-product="{pdata.replace(chr(34), '&quot;')}">
          <div class="product-emoji {cat}">{emoji}</div>
          <div class="product-info">
            <div class="product-name">{p['name']}</div>
            <div class="product-ingredients">成分：{ingredients}</div>
            <div class="product-reason">{p.get('reason', '')}</div>
            <div class="product-price">¥{price_val:.0f}</div>
          </div>
          <div class="stepper">
            <button class="stepper-btn" onclick="stepperChange('{sku}',-1)" aria-label="减少">−</button>
            <span class="stepper-qty" id="qty-{sku}">0</span>
            <button class="stepper-btn plus" onclick="stepperChange('{sku}',1)" aria-label="增加">+</button>
          </div>
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
  <div class="seal">🌿</div>
  <h1>个人调理报告</h1>
  <div class="subtitle">焙 草 集</div>{f'<div class="name">{name}</div>' if name else ''}
  <div class="date">{today}</div>
</div>

<div class="section">
  <div class="section-header">
    <div class="section-icon constitution">🌡</div>
    <div class="section-title">体质倾向</div>
  </div>
  <div class="constitution-badge">{report['constitution_type']}</div>
  <div class="constitution-desc">{report['constitution_desc']}</div>
</div>

<div class="section">
  <div class="section-header">
    <div class="section-icon food">🍽</div>
    <div class="section-title">食养方向</div>
  </div>
  <div class="advice-text">{report['food_advice']}</div>
</div>

<div class="section">
  <div class="section-header">
    <div class="section-icon lifestyle">🧘</div>
    <div class="section-title">生活小贴士</div>
  </div>
  <div class="advice-text">{report['lifestyle_advice']}</div>
</div>

<div class="section">
  <div class="section-header">
    <div class="section-icon seasonal">🍂</div>
    <div class="section-title">顺应季节</div>
  </div>
  <div class="advice-text">{report['seasonal_advice']}</div>
</div>

<div class="divider">· 为 你 推 荐 ·</div>

<div class="section">
  <div class="section-header">
    <div class="section-icon product">✨</div>
    <div class="section-title">推荐食单</div>
  </div>
  {products_html}
</div>

<div class="disclaimer-box">
  <p>本报告基于传统食养理念，仅为调理建议参考。</p>
  <p>不构成医疗诊断。如有健康问题请咨询执业医师。</p>
</div>

<div class="footer">
  <p>焙草集 · 药食同源</p>
</div>

<div id="toast"></div>

<div id="cart-bar" onclick="checkout()">
  <span style="display:flex;align-items:center;gap:10px">
    <span class="cart-icon">🛒<span class="cart-badge" id="cart-count">0</span></span>
    <span class="cart-total" id="cart-total">¥0</span>
  </span>
  <span style="opacity:0.6">去结算 ▸</span>
</div>

<div id="order-overlay" onclick="closeOrder(event)">
  <div id="order-modal" onclick="event.stopPropagation()"></div>
</div>

<button class="btn-back" onclick="window.close()">返回对话</button>

<script>
const Cart = {{
  _items: [],
  add(p) {{
    var ex = this._items.find(i => i.sku_id === p.sku_id);
    if (ex) {{ ex.quantity = Math.min(99, ex.quantity + 1); }}
    else {{ this._items.push({{sku_id:p.sku_id,name:p.name,price:p.price||0,category:p.category||'',quantity:1}}); }}
    this._notify();
  }},
  remove(sku) {{ this._items = this._items.filter(i => i.sku_id !== sku); this._notify(); }},
  setQty(sku, q) {{
    if (q < 1) {{ this.remove(sku); return; }}
    var it = this._items.find(i => i.sku_id === sku);
    if (it) {{ it.quantity = Math.min(99, q); this._notify(); }}
  }},
  count() {{ return this._items.reduce((s,i) => s + i.quantity, 0); }},
  total() {{ return this._items.reduce((s,i) => s + (i.price||0)*i.quantity, 0); }},
  clear() {{ this._items = []; this._notify(); }},
  _notify() {{
    var c = this.count(), t = this.total();
    document.getElementById('cart-count').textContent = c;
    document.getElementById('cart-total').textContent = '¥' + t;
    var bar = document.getElementById('cart-bar');
    if (c > 0) {{ bar.classList.add('show'); document.body.style.paddingBottom = '70px'; }}
    else {{ bar.classList.remove('show'); document.body.style.paddingBottom = ''; }}
    this._items.forEach(function(it) {{
      var el = document.getElementById('qty-' + it.sku_id);
      if (el) {{ el.textContent = it.quantity; }}
    }});
    document.querySelectorAll('.stepper-btn:not(.plus)').forEach(function(b) {{
      var card = b.closest('.rec-card');
      if (card) {{
        var sku = card.getAttribute('data-sku');
        var item = Cart._items.find(i => i.sku_id === sku);
        b.disabled = !item || item.quantity < 1;
      }}
    }});
  }}
}};

function stepperChange(sku, delta) {{
  var card = document.querySelector('.rec-card[data-sku="' + sku + '"]');
  if (!card) return;
  var raw = card.getAttribute('data-product');
  if (!raw) return;
  var prod = JSON.parse(raw.replace(/&quot;/g, '"'));
  var it = Cart._items.find(i => i.sku_id === sku);
  var qty = it ? it.quantity : 0;
  var nq = qty + delta;
  if (nq < 1) {{ Cart.remove(sku); }}
  else if (qty === 0) {{ Cart.add(prod); }}
  else {{ Cart.setQty(sku, nq); }}
}}

function checkout() {{
  if (!Cart.count()) {{ showToast('请先选择商品'); return; }}
  var items = Cart._items;
  var total = Cart.total(), count = Cart.count();
  var itemsHtml = '';
  items.forEach(function(i) {{
    itemsHtml += '<div class="order-item"><span>' + i.name + ' ×' + i.quantity + '</span><span>¥' + (i.price*i.quantity) + '</span></div>';
  }});
  var orderNo = 'BCJ' + Date.now().toString(36).toUpperCase();
  var now = new Date();
  var ts = now.getFullYear()+'-'+(now.getMonth()+1)+'-'+now.getDate()+' '+now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
  document.getElementById('order-modal').innerHTML =
    '<div class="order-check">✓</div>' +
    '<div class="order-title">订单确认</div>' +
    '<div class="order-no">订单号: ' + orderNo + ' ｜ ' + ts + '</div>' +
    '<div class="order-section" style="margin-top:16px"><div style="font-size:13px;font-weight:600;color:#999;margin-bottom:8px">商品明细</div>' + itemsHtml +
    '<div class="order-total-row"><span>合计</span><span style="color:#c0392b">' + count + ' 件 共 ¥' + total + '</span></div></div>' +
    '<div class="order-section" style="font-size:13px;color:#999"><p>📍 取货方式：到店自取</p><p>🏪 门店地址：焙草集门店</p><p style="margin-top:4px;font-size:11px;color:#bbb">此为模拟订单，实际支付将对接有赞</p></div>' +
    '<div class="order-actions"><button class="btn-close" onclick="closeOrder()">继续选购</button><button class="btn-confirm" data-orderno="' + orderNo + '" onclick="confirmOrder(this.dataset.orderno)">确认下单</button></div>';
  document.getElementById('order-overlay').classList.add('show');
}}

function closeOrder(e) {{
  if (e && e.target !== document.getElementById('order-overlay')) return;
  document.getElementById('order-overlay').classList.remove('show');
}}

function confirmOrder(orderNo) {{
  Cart.clear();
  document.getElementById('order-overlay').classList.remove('show');
  var sec = document.querySelector('.section:last-of-type');
  if (sec) {{
    var div = document.createElement('div');
    div.style.cssText = 'text-align:center;padding:16px;margin:14px;background:#e8f5e9;border-radius:12px;font-size:14px;font-weight:600;color:#5B8C5A';
    div.innerHTML = '✅ 下单成功！<br><span style="font-size:12px;font-weight:400">订单号: ' + orderNo + '</span><br><span style="font-size:11px;color:#999">请到店出示订单号取货</span>';
    sec.parentNode.insertBefore(div, sec.nextSibling);
  }}
  showToast('下单成功 ✓');
}}

function showToast(msg) {{
  var t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(function() {{ t.classList.remove('show'); }}, 2000);
}}
</script>

</body>
</html>"""
    return HTMLResponse(html)
