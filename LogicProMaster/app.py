import streamlit as st
import streamlit.components.v1 as components
import json
import time
import os

try:
    from scraper import MTLiveScraper
except ImportError:
    MTLiveScraper = None

st.set_page_config(page_title="LogicProAi 終極融合版 (MT-Live)", layout="wide", initial_sidebar_state="expanded")

if 'history' not in st.session_state: st.session_state.history = []
if 'scraper_instance' not in st.session_state: st.session_state.scraper_instance = None
if 'auto_sync' not in st.session_state: st.session_state.auto_sync = False

# ================= 側邊欄設定 =================
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
c_b, c_p, c_t = st.sidebar.columns(3)
if c_b.button("🔴 莊", use_container_width=True): st.session_state.history.append('B')
if c_p.button("🔵 閒", use_container_width=True): st.session_state.history.append('P')
if c_t.button("🟢 和", use_container_width=True): st.session_state.history.append('T')

c_undo, c_clear = st.sidebar.columns(2)
if c_undo.button("退回一局", use_container_width=True) and st.session_state.history: st.session_state.history.pop()
if c_clear.button("重置牌靴", use_container_width=True): st.session_state.history = []

if st.session_state.auto_sync and st.session_state.scraper_instance:
    new_data = st.session_state.scraper_instance.get_live_scores()
    if new_data: pass
    time.sleep(2)
    st.rerun()

# ================= 核心融合引擎 =================
st.markdown("### 🃏 MT Live 百家樂：多維路單與旗艦預測系統 (AI 防禦機制已啟動)")

html_path = "index.html"

if not os.path.exists(html_path):
    st.error(f"❌ 找不到 `{html_path}` 檔案！")
else:
    # 讀取主 HTML
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 嘗試讀取獨立的 CSS 與 JS 檔案 (如果有)
    css_content = ""
    if os.path.exists("style.css"):
        with open("style.css", "r", encoding="utf-8") as f:
            css_content = f.read()
            
    js_content = ""
    if os.path.exists("app.js"):
        with open("app.js", "r", encoding="utf-8") as f:
            js_content = f.read()

    # 將 Python 的路單數據轉換為 JSON
    python_history_json = json.dumps(st.session_state.history)

    # 構建強勢注入腳本：將 CSS、JS 及數據直接嵌入 HTML
    injection_code = f"""
    <style>
        /* 隱藏原本介面的輸入按鈕，避免與左側 Python 側邊欄衝突 */
        .direct-input-container, .btn-group, .batch-input-group {{ display: none !important; }}
        {css_content}
    </style>
    <script>
        // 1. 強制將 Python 傳來的數據設定為全域變數
        window.baccaratHistory = {python_history_json};
        
        // 2. 載入原本的 JS 邏輯
        {js_content}
        
        // 3. 確保畫面重繪 (如果你的 JS 中有特定的繪圖函數，可以在這裡呼叫，例如 renderRoads())
        // renderRoads(); 
    </script>
    """
    
    # 將注入腳本放入 HTML 的尾端，確保覆蓋原本設定
    html_content = html_content.replace("</body>", f"{injection_code}</body>")

    # 渲染最終畫面
    components.html(html_content, height=900, scrolling=True)
