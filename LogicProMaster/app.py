import streamlit as st
import streamlit.components.v1 as components
import json
import time
import os

try:
    from scraper import MTLiveScraper
except ImportError:
    MTLiveScraper = None

# ==========================================
# 1. 網頁頂層配置
# ==========================================
st.set_page_config(
    page_title="LogicProAi 終極融合版 (MT-Live)", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 初始化核心數據 Session State (統一使用 list 追蹤歷史，不再只記總數)
if 'history' not in st.session_state:
    st.session_state.history = []
if 'scraper_instance' not in st.session_state: 
    st.session_state.scraper_instance = None
if 'auto_sync' not in st.session_state: 
    st.session_state.auto_sync = False

# ==========================================
# 2. 側邊欄：控制面板與爬蟲設定
# ==========================================
st.sidebar.markdown("### 🔌 自動盯盤抓取設定")
casino_url = st.sidebar.text_input("娛樂城登入網址", value="https://example-casino.com")

col_auto1, col_auto2 = st.sidebar.columns(2)
with col_auto1:
    if st.sidebar.button("🔗 啟動瀏覽器", use_container_width=True):
        if MTLiveScraper:
            st.session_state.scraper_instance = MTLiveScraper(casino_url)
            st.session_state.scraper_instance.start_monitoring()
            st.sidebar.success("✅ 瀏覽器就緒")
        else:
            st.sidebar.error("找不到 scraper.py")
with col_auto2:
    st.session_state.auto_sync = st.sidebar.checkbox("🔄 開啟同步", value=st.session_state.auto_sync)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ 手動輸入區 (Python 端)")

# 建立手動輸入按鈕
c_b, c_p, c_t = st.sidebar.columns(3)
if c_b.button("🔴 莊", use_container_width=True):
    st.session_state.history.append('B')
if c_p.button("🔵 閒", use_container_width=True):
    st.session_state.history.append('P')
if c_t.button("🟢 和", use_container_width=True):
    st.session_state.history.append('T')

c_undo, c_clear = st.sidebar.columns(2)
if c_undo.button("退回一局", use_container_width=True) and st.session_state.history:
    st.session_state.history.pop()
if c_clear.button("重置牌靴", use_container_width=True):
    st.session_state.history = []

# 模擬爬蟲同步邏輯 (若有串接真實爬蟲，可在此更新 st.session_state.history)
if st.session_state.auto_sync and st.session_state.scraper_instance:
    # 假設 scraper 會回傳最新的一局賽果字串 (例如 'B', 'P', 'T') 或整個陣列
    new_data = st.session_state.scraper_instance.get_live_scores()
    if new_data:
        # 更新邏輯視你的 scraper 實作而定
        pass 
    time.sleep(2) # 溫和刷新頻率
    st.rerun()

# ==========================================
# 3. 核心融合引擎：讀取並注入 LogicProAi (index.html)
# ==========================================
st.markdown("### 🃏 MT Live 百家樂：多維路單與旗艦預測系統 (AI 防禦機制已啟動)")

html_path = "index.html"

if not os.path.exists(html_path):
    st.error(f"❌ 找不到 `{html_path}` 檔案！請確保你把 LogicProAi 的 `index.html` 放在與 `app.py` 同一個資料夾下。")
else:
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 【黑客級注入 1】: 隱藏原本 HTML 內建的按鈕，改由 Streamlit 側邊欄控制，避免兩邊狀態不同步
    css_injection = """
    <style>
        .direct-input-container, .btn-group, .batch-input-group { display: none !important; }
        body { padding-bottom: 20px; } /* 微調間距 */
    </style>
    """
    html_content = html_content.replace("</head>", f"{css_injection}</head>")

    # 【黑客級注入 2】: 將 Python 的歷史紀錄陣列，覆蓋掉 JS 初始化的空陣列
    python_history_json = json.dumps(st.session_state.history)
    html_content = html_content.replace(
        "let baccaratHistory = [];", 
        f"let baccaratHistory = {python_history_json};"
    )

    # 渲染注入後的 HTML 引擎
    components.html(html_content, height=1200, scrolling=True)
