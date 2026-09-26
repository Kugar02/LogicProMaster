import streamlit as st
import pandas as pd

# 嘗試載入計算引擎 (請確保你的 engine.py 在同一個資料夾)
try:
    from engine import run_monte_carlo_with_kelly
except ImportError:
    run_monte_carlo_with_kelly = None

# ================= 1. 系統全域設定 =================
st.set_page_config(page_title="Quantum Baccarat OS", layout="wide", initial_sidebar_state="collapsed")

# 自訂原生 CSS 樣式 (隱藏預設留白，美化按鈕)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
        .stButton>button { height: 50px; font-size: 18px; font-weight: bold; border-radius: 8px; }
        .b-btn { background-color: #ff4b4b !important; color: white !important; }
        .p-btn { background-color: #1f77b4 !important; color: white !important; }
        .t-btn { background-color: #2ca02c !important; color: white !important; }
        .road-container { background: white; padding: 10px; border-radius: 8px; overflow-x: auto; margin-bottom: 20px;}
        .ask-road-box { background: #f0f2f6; border-radius: 8px; padding: 15px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 初始化資料庫
if 'history' not in st.session_state: st.session_state.history = []
if 'bankroll' not in st.session_state: st.session_state.bankroll = 10000

# ================= 2. 頂部控制台 =================
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
st.session_state.bankroll = c1.number_input("💰 總本金 ($)", min_value=100, value=st.session_state.bankroll, step=500)
sim_runs = c2.selectbox("⚡ AI 深度", [5000, 10000, 20000], index=1)
if c3.button("🗑️ 清空歷史 (新靴)", use_container_width=True): 
    st.session_state.history = []
    st.rerun()
if c4.button("↩️ 撤銷上一手", use_container_width=True): 
    if st.session_state.history: st.session_state.history.pop()

# 實時開牌輸入區
st.markdown("### 🎛️ 開牌輸入")
btn_col1, btn_col2, btn_col3 = st.columns(3)
if btn_col1.button("🔴 開莊 (Banker)", use_container_width=True): st.session_state.history.append('B')
if btn_col2.button("🔵 開閒 (Player)", use_container_width=True): st.session_state.history.append('P')
if btn_col3.button("🟢 開和 (Tie)", use_container_width=True): st.session_state.history.append('T')

st.markdown("---")

# ================= 3. AI 數學分析核心 =================
st.markdown("### 🧠 AI 核心分析與決策")

total_hands = len(st.session_state.history)
b_count = st.session_state.history.count('B')
p_count = st.session_state.history.count('P')
t_count = st.session_state.history.count('T')

ai_recommend = "等待數據..."
ai_bet_amount = 0

if total_hands > 0 and run_monte_carlo_with_kelly:
    with st.spinner("AI 高速運算中..."):
        avg_tc, b_prob, p_prob, t_prob, recommend, k_percent, s_bet = run_monte_carlo_with_kelly(
            b_count, p_count, t_count, bankroll=st.session_state.bankroll, sim_count=sim_runs
        )
        ai_recommend = recommend
        ai_bet_amount = s_bet
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("精算真數 (TC)", f"{avg_tc:.2f}")
        m2.metric("莊家修正勝率", f"{b_prob:.2f}%")
        m3.metric("閒家修正勝率", f"{p_prob:.2f}%")
        m4.metric("和局預估機率", f"{t_prob:.2f}%")

        if s_bet > 0:
            st.success(f"🔥 **AI 決策信號：{recommend}** ｜ 💵 建議注碼：**${s_bet}**")
        else:
            st.warning(f"🛡️ **防禦信號：{recommend}** (負期望值，強制停注觀望)")

# ================= 4. 原生百家樂路單引擎 (Python -> HTML) =================

def generate_big_road_matrix(history, rows=6, cols=36):
    """百家樂大路核心演算法 (支援長龍向右拐彎與和局記錄)"""
    grid = {}
    curr_col, curr_row = 0, 0
    start_col = 0
    last_real = None
    
    for item in history:
        if item == 'T':
            if last_real is not None:
                if 'ties' not in grid[(curr_col, curr_row)]:
                    grid[(curr_col, curr_row)]['ties'] = 1
                else:
                    grid[(curr_col, curr_row)]['ties'] += 1
            continue
            
        if last_real is None:
            last_real = item
            grid[(curr_col, curr_row)] = {'val': item, 'ties': 0}
        elif item == last_real:
            curr_row += 1
            # 處理長龍向下碰底或撞到其他棋子的「向右拐彎」機制
            if curr_row >= rows or (curr_col, curr_row) in grid:
                curr_row -= 1
                curr_col += 1
            grid[(curr_col, curr_row)] = {'val': item, 'ties': 0}
        else:
            last_real = item
            start_col += 1
            curr_col = start_col
            # 尋找第 0 行第一個空的欄位開新路
            while (curr_col, 0) in grid:
                curr_col += 1
            start_col = curr_col
            curr_row = 0
            grid[(curr_col, curr_row)] = {'val': item, 'ties': 0}
            
    return grid

def render_html_grid(grid, rows=6, cols=36, cell_size=28, is_bead=False):
    """將 Python 矩陣渲染成精緻的 HTML 表格"""
    html = f'<table style="border-collapse: collapse; background: #fff; table-layout: fixed; border: 2px solid #666;">'
    for r in range(rows):
        html += '<tr>'
        for c in range(cols):
            cell = grid.get((c, r), None)
            content = ""
            if cell:
                val = cell['val'] if isinstance(cell, dict) else cell
                ties = cell.get('ties', 0) if isinstance(cell, dict) else 0
                
                # 樣式定義
                if is_bead:
                    bg = "#ff4b4b" if val == 'B' else "#1f77b4" if val == 'P' else "#2ca02c"
                    txt = "莊" if val == 'B' else "閒" if val == 'P' else "和"
                    content = f'<div style="width:22px;height:22px;background:{bg};color:white;border-radius:50%;font-size:12px;line-height:22px;text-align:center;margin:auto;">{txt}</div>'
                else:
                    color = "#ff4b4b" if val == 'B' else "#1f77b4"
                    content = f'<div style="position:relative;width:20px;height:20px;border:3px solid {color};border-radius:50%;margin:auto;">'
                    if ties > 0:
                        content += f'<div style="position:absolute;width:24px;height:3px;background:#2ca02c;transform:rotate(-45deg);top:8px;left:-4px;"></div>'
                    content += '</div>'
                    
            html += f'<td style="border: 1px solid #ddd; width: {cell_size}px; height: {cell_size}px; text-align: center; vertical-align: middle;">{content}</td>'
        html += '</tr>'
    html += '</table>'
    return html

st.markdown("---")
st.markdown("### 📊 標準歷史路單")

# 準備大路數據
big_road_grid = generate_big_road_matrix(st.session_state.history, cols=36)
big_road_html = render_html_grid(big_road_grid, rows=6, cols=36, cell_size=28, is_bead=False)

# 準備珠盤路數據 (簡單的由上而下，由左至右)
bead_grid = {}
for i, res in enumerate(st.session_state.history):
    bead_grid[(i // 6, i % 6)] = res
bead_html = render_html_grid(bead_grid, rows=6, cols=14, cell_size=28, is_bead=True)

col_road1, col_road2 = st.columns([1.5, 3])
with col_road1:
    st.caption("珠盤路 (Bead Plate)")
    st.markdown(f'<div class="road-container">{bead_html}</div>', unsafe_allow_html=True)
with col_road2:
    st.caption("大路 (Big Road) - 自動長龍拐彎")
    st.markdown(f'<div class="road-container">{big_road_html}</div>', unsafe_allow_html=True)

# ================= 5. 莊閒問路 (模擬預測) =================
st.markdown("### 🔮 莊閒問路 (AI 下局走勢預測)")
ask_b_col, ask_p_col = st.columns(2)

# 問路邏輯：模擬下一局如果是莊或閒，AI的推薦與狀態
with ask_b_col:
    st.markdown("""
    <div class="ask-road-box">
        <h4 style="color:#ff4b4b; margin-top:0;">🔴 若下局開【莊】</h4>
        <p style="font-size:14px; color:#666;">大路將呈現紅色圈連線，真數 (TC) 偏向下降。</p>
    </div>
    """, unsafe_allow_html=True)
    if "莊" in ai_recommend:
        st.success("✨ 符合當前 AI 資金進場模型")

with ask_p_col:
    st.markdown("""
    <div class="ask-road-box">
        <h4 style="color:#1f77b4; margin-top:0;">🔵 若下局開【閒】</h4>
        <p style="font-size:14px; color:#666;">大路將呈現藍色圈連線，真數 (TC) 偏向攀升。</p>
    </div>
    """, unsafe_allow_html=True)
    if "閒" in ai_recommend:
        st.success("✨ 符合當前 AI 資金進場模型")
