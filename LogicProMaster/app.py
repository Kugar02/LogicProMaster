import streamlit as st
import pandas as pd
from engine import run_monte_carlo_with_kelly
from drive_logger import upload_shoe_to_kugar

st.set_page_config(page_title="Quantum Baccarat Dynamic OS", layout="wide", page_icon="🎲")

# 1. 防禦性 session_state 初始化
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 10000.0
if 'history_list' not in st.session_state:
    st.session_state.history_list = []
if 'ai_targets' not in st.session_state:
    st.session_state.ai_targets = []
if 'total_profit' not in st.session_state:
    st.session_state.total_profit = 0.0

kelly_suggest = False  # 防止渲染時出現 NameError

st.title("🎲 Quantum Baccarat Dynamic OS")

# 側邊欄資金管理
st.sidebar.header("⚙️ 資金管理與控制")
st.session_state.bankroll = st.sidebar.number_input("💰 當前總資金 ($)", value=st.session_state.bankroll, step=100.0)

# Google Drive 一鍵備份
st.sidebar.markdown("---")
st.sidebar.subheader("📁 Google Drive 數據備份")

if st.sidebar.button("📦 一鍵備份當前牌靴至 KUGAR"):
    with st.spinner("正在備份至 Google Drive KUGAR 資料夾..."):
        success, result = upload_shoe_to_kugar(
            shoe_history=st.session_state.history_list,
            session_stats={"bankroll": st.session_state.bankroll}
        )
        if success:
            st.sidebar.success("✅ 牌靴已成功保存至 KUGAR！")
            st.sidebar.markdown(f"[🔗 在 Google Drive 查看檔案]({result})")
        else:
            st.sidebar.error(result)

# 開牌快捷按鈕介面
st.subheader("🎛️ 開牌紀錄與快捷輸入")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🔴 開莊 (B)", use_container_width=True):
        st.session_state.history_list.append("B")
        st.rerun()
with c2:
    if st.button("🔵 開閒 (P)", use_container_width=True):
        st.session_state.history_list.append("P")
        st.rerun()
with c3:
    if st.button("🟢 開和 (T)", use_container_width=True):
        st.session_state.history_list.append("T")
        st.rerun()
with c4:
    if st.button("↩️ 撤銷上一手", use_container_width=True):
        if st.session_state.history_list:
            st.session_state.history_list.pop()
            st.rerun()

# 批量載入歷史
batch_input = st.text_input("📝 批量輸入歷史賽果 (例如: BBPPBPT)", "")
if st.button("📥 一鍵載入歷史紀錄"):
    if batch_input:
        clean_input = [x.upper() for x in batch_input.strip() if x.upper() in ['B', 'P', 'T']]
        st.session_state.history_list = clean_input
        st.rerun()

if st.button("🗑️ 清空重置 (新靴)"):
    if len(st.session_state.history_list) > 0:
        upload_shoe_to_kugar(st.session_state.history_list)
    st.session_state.history_list = []
    st.session_state.ai_targets = []
    st.rerun()

# 計算統計數據
history = st.session_state.history_list
b_count = history.count('B')
p_count = history.count('P')
t_count = history.count('T')
total_hands = len(history)

# 核心推理引擎觸發
if total_hands > 0:
    avg_tc, final_b_pct, final_p_pct, actual_t_ratio, recommend, four_roads_data, is_break_active, consec_losses, markov_status, is_resonance, confidence_pct = run_monte_carlo_with_kelly(
        b_count, p_count, t_count,
        bankroll=st.session_state.bankroll,
        sim_count=0,
        history_list=history,
        ai_targets=st.session_state.ai_targets
    )

    st.markdown("---")
    st.header(f"🎯 最終權重建議：{recommend}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("莊家歸一化權重", f"{final_b_pct}%")
    m2.metric("閒家歸一化權重", f"{final_p_pct}%")
    m3.metric("訊號可信度指數", f"{confidence_pct}%")

    st.caption(markov_status)

    st.markdown("### 🔍 4 大核心路單獨立診斷")
    r_cols = st.columns(4)
    for idx, (rk, rv) in enumerate(four_roads_data.items()):
        with r_cols[idx]:
            st.markdown(f"**{rv['name']}**")
            st.write(rv['status'])
            if rv['details']:
                st.caption(" • " + "\n • ".join(rv['details']))

st.markdown("---")
st.write(f"📊 當前歷史記錄 (共 {total_hands} 局): ", " ".join(history[-30:]))
