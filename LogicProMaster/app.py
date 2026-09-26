import streamlit as st
import streamlit.components.v1 as components
import json
import time
import os

try:
    from scraper import MTLiveScraper
except ImportError:
    MTLiveScraper = None

# 1. 頁面設定：強制滿版寬度
st.set_page_config(page_title="LogicProMaster 終極版", layout="wide")

# 2. 隱藏 Streamlit 預設的 Header, Footer 與多餘 Padding
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state: st.session_state.history = []
if 'scraper_instance' not in st.session_state: st.session_state.scraper_instance = None
if 'auto_sync' not in st.session_state: st.session_state.auto_sync = False

# ================= 頂部控制列 (取代側邊欄) =================

# 將爬蟲與系統設定收納進隱藏面板，保持主畫面乾淨
with st.expander("⚙️ MT-Live 自動抓取系統與參數設定", expanded=False):
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    casino_url = c1.text_input("娛樂城網址", value="https://dg38.net/action/Opengame/freegame.aspx")
    
    if c2.button("🔗 啟動瀏覽器", use_container_width=True):
        if MTLiveScraper:
            st.session_state.scraper_instance = MTLiveScraper(casino_url)
            st.session_state.scraper_instance.start_monitoring()
            st.success("✅ 就緒")
        else:
            st.error("找不到 scraper.py")
    
    st.session_state.auto_sync = c3.checkbox("🔄 開啟同步", value=st.session_state.auto_sync)
    if c4.button("🗑️ 重置牌靴", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# 實時開牌輸入區 (橫向置中精簡版)
st.markdown("### 🎛️ 手動開牌紀錄")
col_b, col_p, col_t, col_undo, _ = st.columns([1, 1, 1, 1, 4])
if col_b.button("🔴 開莊 (B)", use_container_width=True): st.session_state.history.append('B')
if col_p.button("🔵 開閒 (P)", use_container_width=True): st.session_state.history.append('P')
if col_t.button("🟢 開和 (T)", use_container_width=True): st.session_state.history.append('T')
if col_undo.button("↩️ 退回一局", use_container_width=True) and st.session_state.history: 
    st.session_state.history.pop()

# 自動同步爬蟲邏輯
if st.session_state.auto_sync and st.session_state.scraper_instance:
    new_data = st.session_state.scraper_instance.get_live_scores()
    if new_data: pass
    time.sleep(2)
    st.rerun()

st.markdown("---")

# ================= 核心融合引擎 (載入 LogicProMaster 前端) =================

# 動態判斷檔案路徑 (支援直接放根目錄，或放在 LogicProMaster 資料夾內)
html_path = "index.html"
css_path = "style.css"
js_path = "app.js"

if not os.path.exists(html_path) and os.path.exists(os.path.join("LogicProMaster", "index.html")):
    html_path = os.path.join("LogicProMaster", "index.html")
    css_path = os.path.join("LogicProMaster", "style.css")
    js_path = os.path.join("LogicProMaster", "app.js")

if not os.path.exists(html_path):
    st.error(f"❌ 找不到 `{html_path}`！請確認檔案位置。")
else:
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    css_content = ""
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
            
    js_content = ""
    if os.path.exists(js_path):
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

    python_history_json = json.dumps(st.session_state.history)

    # 注入樣式與腳本
    injection_code = f"""
    <style>
        /* 隱藏 HTML 內建的按鈕列，避免與 Streamlit 的 Python 按鈕重複 */
        .direct-input-container, .btn-group, .batch-input-group {{ display: none !important; }}
        /* 去除 iframe 內的預設背景留白 */
        body {{ background-color: transparent !important; margin: 0; padding: 0; }}
        {css_content}
    </style>
    <script>
        window.baccaratHistory = {python_history_json};
        {js_content}
    </script>
    """
    
    html_content = html_content.replace("</body>", f"{injection_code}</body>")

    # 將高度拉大至 1200px 確保四大路與下三路完整呈現無需捲動
    components.html(html_content, height=1200, scrolling=True)
