import streamlit as st
import pandas as pd
from engine import run_monte_carlo_with_kelly
from drive_logger import upload_shoe_to_kugar

st.set_page_config(page_title="Quantum Baccarat Dynamic OS", layout="wide", page_icon="🎲")

# ==============================================================================
# 1. 防禦性 Session State 初始化
# ==============================================================================
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 10000.0
if 'history_list' not in st.session_state:
    st.session_state.history_list = []
if 'ai_targets' not in st.session_state:
    st.session_state.ai_targets = []
if 'total_profit' not in st.session_state:
    st.session_state.total_profit = 0.0

st.title("🎲 Quantum Baccarat Dynamic OS")

# ==============================================================================
# 2. 側邊欄資金管理與 Google Drive 備份
# ==============================================================================
st.sidebar.header("⚙️ 資金管理與控制")
st.session_state.bankroll = st.sidebar.number_input("💰 當前總資金 ($)", value=float(st.session_state.bankroll), step=100.0)

# 顯示累計盈虧
profit_color = "green" if st.session_state.total_profit >= 0 else "red"
st.sidebar.markdown(f"**累計盈虧：** <span style='color:{profit_color};font-size:18px;'>${st.session_state.total_profit:+.2f}</span>", unsafe_allow_html=True)

if st.sidebar.button("🔄 重置資金與盈虧"):
    st.session_state.total_profit = 0.0
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📁 Google Drive 數據備份")

if st.sidebar.button("📦 一鍵備份當前牌靴至 KUGAR", use_container_width=True):
    with st.spinner("正在備份至 Google Drive KUGAR 資料夾..."):
        success, result = upload_shoe_to_kugar(
            shoe_history=st.session_state.history_list,
            session_stats={
                "bankroll": st.session_state.bankroll,
                "total_profit": st.session_state.total_profit
            }
        )
        if success:
            st.sidebar.success("✅ 牌靴已成功保存至 KUGAR！")
            st.sidebar.markdown(f"[🔗 在 Google Drive 查看檔案]({result})")
        else:
            st.sidebar.error(result)

# ==============================================================================
# 3. 開牌紀錄與快捷輸入介面
# ==============================================================================
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

batch_input = st.text_input("📝 批量輸入歷史賽果 (例如: BBPPBPT)", "")
col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("📥 一鍵載入歷史紀錄", use_container_width=True):
        if batch_input:
            clean_input = [x.upper() for x in batch_input.strip() if x.upper() in ['B', 'P', 'T']]
            st.session_state.history_list = clean_input
            st.rerun()
with col_b2:
    if st.button("🗑️ 清空重置 (新靴)", use_container_width=True):
        if len(st.session_state.history_list) > 0:
            upload_shoe_to_kugar(st.session_state.history_list)
        st.session_state.history_list = []
        st.session_state.ai_targets = []
        st.rerun()

# ==============================================================================
# 4. 核心推理引擎計算與 AI 決策顯示
# ==============================================================================
history = st.session_state.history_list
b_count = history.count('B')
p_count = history.count('P')
t_count = history.count('T')
total_hands = len(history)

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
    
    # ------------------ 下注統計與 Kelly 注碼計算區塊 ------------------
    # 根據勝率優勢計算 Half-Kelly 下注比例
    win_p = max(final_b_pct, final_p_pct) / 100.0
    edge = (win_p - (1 - win_p))
    
    # 若觀望或無優勢，注碼為0
    if "觀望" in recommend or edge <= 0:
        kelly_fraction = 0.0
        suggested_bet = 0.0
    else:
        # 半凱利公式 (Half-Kelly) 避險風險控管
        kelly_fraction = max(0.0, min(0.08, (edge / 1.0) * 0.5))
        suggested_bet = round(st.session_state.bankroll * kelly_fraction, 0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 莊家歸一化權重", f"{final_b_pct}%")
    m2.metric("🔵 閒家歸一化權重", f"{final_p_pct}%")
    m3.metric("🎯 訊號可信度", f"{confidence_pct}%")
    m4.metric("💵 推薦下注金額 (半凱利)", f"${suggested_bet:.0f}", help="基於當前可信度與優勢計算之 Half-Kelly 安全注碼")

    if is_break_active:
        st.warning(f"⚠️ 觸發智能防禦反打機制 (連續未命中: {consec_losses} 手)")
    if is_resonance:
        st.success("🔥 下三路三路極致共振爆發點！")

    st.caption(markov_status)

    # ------------------ 4 大核心路單診斷區塊 ------------------
    st.markdown("### 🔍 4 大核心路單獨立診斷")
    r_cols = st.columns(4)
    for idx, (rk, rv) in enumerate(four_roads_data.items()):
        with r_cols[idx]:
            st.markdown(f"**{rv['name']}**")
            st.write(rv['status'])
            if rv['details']:
                st.caption(" • " + "\n • ".join(rv['details']))

    # ==============================================================================
    # 5. 視覺化路紙介面 (珠盤路 & 大路矩陣)
    # ==============================================================================
    st.markdown("---")
    st.markdown("### 📜 視覺化路紙介面")

    tab_bead, tab_big = st.tabs(["🔴🔵 珠盤路 (Bead Plate)", "📊 大路 columns (Big Road)"])

    # --- A. 珠盤路 (直向 6 格矩陣) ---
    with tab_bead:
        bead_rows = [[] for _ in range(6)]
        for idx, item in enumerate(history):
            r = idx % 6
            if item == 'B':
                badge = "<span style='background-color:#E74C3C;color:white;padding:2px 8px;border-radius:50%;font-weight:bold;'>莊</span>"
            elif item == 'P':
                badge = "<span style='background-color:#3498DB;color:white;padding:2px 8px;border-radius:50%;font-weight:bold;'>閒</span>"
            else:
                badge = "<span style='background-color:#2ECC71;color:white;padding:2px 8px;border-radius:50%;font-weight:bold;'>和</span>"
            bead_rows[r].append(badge)

        html_table = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
        for row in bead_rows:
            html_table += "<tr style='height:35px;'>"
            for cell in row:
                html_table += f"<td style='border:1px solid #333;'>{cell}</td>"
            html_table += "</tr>"
        html_table += "</table>"
        st.markdown(html_table, unsafe_allow_html=True)

    # --- B. 大路矩陣 ---
    with tab_big:
        big_cols = []
        cur_col = []
        last_val = None
        for item in history:
            if item == 'T':
                continue
            if item != last_val:
                if cur_col:
                    big_cols.append(cur_col)
                cur_col = [item]
                last_val = item
            else:
                cur_col.append(item)
        if cur_col:
            big_cols.append(cur_col)

        # 顯示最近 20 列大路
        display_cols = big_cols[-20:]
        if display_cols:
            max_r = max(len(c) for c in display_cols)
            grid = [["" for _ in range(len(display_cols))] for _ in range(max_r)]
            for c_idx, col_data in enumerate(display_cols):
                for r_idx, val in enumerate(col_data):
                    if val == 'B':
                        grid[r_idx][c_idx] = "<span style='color:#E74C3C;font-weight:bold;'>🔴 莊</span>"
                    else:
                        grid[r_idx][c_idx] = "<span style='color:#3498DB;font-weight:bold;'>🔵 閒</span>"

            big_html = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
            for row in grid:
                big_html += "<tr style='height:30px;'>"
                for cell in row:
                    big_html += f"<td style='border:1px solid #444;'>{cell}</td>"
                big_html += "</tr>"
            big_html += "</table>"
            st.markdown(big_html, unsafe_allow_html=True)

st.markdown("---")
st.write(f"📊 當前歷史記錄 (共 {total_hands} 局): ", " ".join(history[-30:]))
