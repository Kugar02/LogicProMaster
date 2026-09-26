import streamlit as st
import pandas as pd
import time

# 嘗試載入計算引擎 (請確保你的 engine.py 在同一個資料夾)
try:
    from engine import run_monte_carlo_with_kelly
except ImportError:
    run_monte_carlo_with_kelly = None

# ================= 1. 系統全域設定 =================
st.set_page_config(page_title="Quantum Baccarat OS", layout="wide", initial_sidebar_state="collapsed")

# 自訂原生 CSS 樣式 (純 Python 渲染，不依賴外部檔案)
st.markdown("""
    <style>
        .stButton>button { height: 60px; font-size: 20px; font-weight: bold; border-radius: 10px; }
        .b-btn { background-color: #ff4b4b !important; color: white !important; }
        .p-btn { background-color: #1f77b4 !important; color: white !important; }
        .t-btn { background-color: #2ca02c !important; color: white !important; }
        .metric-box { background-color: #262730; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #444; }
        .road-map-container { display: flex; flex-wrap: wrap; gap: 5px; background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
        .road-bead { width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; font-size: 14px; }
        .bead-b { background-color: #ff4b4b; box-shadow: 0 0 5px #ff4b4b; }
        .bead-p { background-color: #1f77b4; box-shadow: 0 0 5px #1f77b4; }
        .bead-t { background-color: #2ca02c; box-shadow: 0 0 5px #2ca02c; }
    </style>
""", unsafe_allow_html=True)

# 初始化資料庫
if 'history' not in st.session_state: st.session_state.history = []
if 'bankroll' not in st.session_state: st.session_state.bankroll = 10000

# ================= 2. 頂部狀態列 =================
st.title("🎯 Quantum Baccarat OS (全新純 Python 核心版)")
st.markdown("放棄所有舊有框架，採用 100% Streamlit 原生渲染，搭載蒙地卡羅與凱利注碼引擎。")

c1, c2, c3 = st.columns(3)
with c1:
    st.session_state.bankroll = st.number_input("💰 當前總本金 (Bankroll)", min_value=100, value=st.session_state.bankroll, step=500)
with c2:
    sim_runs = st.selectbox("⚡ AI 模擬深度", [5000, 10000, 20000], index=1)
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ 清空歷史紀錄 (新牌靴)", use_container_width=True):
        st.session_state.history = []
        st.rerun()

st.markdown("---")

# ================= 3. 實時輸入控制台 =================
st.markdown("### 🎛️ 開牌輸入區")
btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

if btn_col1.button("🔴 莊家 (Banker)", use_container_width=True): 
    st.session_state.history.append('B')
if btn_col2.button("🔵 閒家 (Player)", use_container_width=True): 
    st.session_state.history.append('P')
if btn_col3.button("🟢 和局 (Tie)", use_container_width=True): 
    st.session_state.history.append('T')
if btn_col4.button("↩️ 撤銷上一手", use_container_width=True): 
    if st.session_state.history: st.session_state.history.pop()

# ================= 4. AI 數學分析核心 =================
st.markdown("### 🧠 量化預測引擎")

b_count = st.session_state.history.count('B')
p_count = st.session_state.history.count('P')
t_count = st.session_state.history.count('T')
total_hands = len(st.session_state.history)

if total_hands == 0:
    st.info("請在上方輸入開牌結果，AI 引擎將自動啟動。")
else:
    # 統計儀表板
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("已開總局數", total_hands)
    m2.metric("莊家開出率", f"{(b_count/total_hands)*100:.1f}%")
    m3.metric("閒家開出率", f"{(p_count/total_hands)*100:.1f}%")
    m4.metric("和局開出率", f"{(t_count/total_hands)*100:.1f}%")

    # 執行蒙地卡羅運算
    if run_monte_carlo_with_kelly:
        with st.spinner(f"正在執行 {sim_runs} 次蒙地卡羅殘牌矩陣運算..."):
            avg_tc, b_prob, p_prob, t_prob, recommend, k_percent, s_bet = run_monte_carlo_with_kelly(
                b_count, p_count, t_count, bankroll=st.session_state.bankroll, sim_count=sim_runs
            )
            
        if avg_tc is not None:
            # 顯示決策信號
            if s_bet > 0:
                st.success(f"🔥 **強勢進場信號：{recommend}**")
                st.markdown(f"### 💵 凱利建議注碼：<span style='color:#00ffcc;'>${s_bet}</span> (佔總資金 {k_percent:.2f}%)", unsafe_allow_html=True)
            else:
                st.warning(f"🛡️ **防禦信號：{recommend}** (當前期望值為負，強制停止下注)")

            # 詳細概率表格
            df_prob = pd.DataFrame({
                "指標": ["真數 (True Count)", "莊家修正勝率", "閒家修正勝率", "和局修正機率"],
                "數值": [f"{avg_tc:.2f}", f"{b_prob:.2f}%", f"{p_prob:.2f}%", f"{t_prob:.2f}%"]
            })
            st.table(df_prob)
    else:
        st.error("找不到 `engine.py`！請確保運算引擎檔案存在。")

st.markdown("---")

# ================= 5. 原生視覺化路紙 (取代 LogicProAi) =================
st.markdown("### 📜 原生歷史珠盤路")
if not st.session_state.history:
    st.write("尚無歷史紀錄")
else:
    # 使用純 HTML/CSS 生成漂亮的珠盤路
    road_html = '<div class="road-map-container">'
    for res in st.session_state.history:
        if res == 'B':
            road_html += '<div class="road-bead bead-b">莊</div>'
        elif res == 'P':
            road_html += '<div class="road-bead bead-p">閒</div>'
        else:
            road_html += '<div class="road-bead bead-t">和</div>'
    road_html += '</div>'
    
    st.markdown(road_html, unsafe_allow_html=True)
