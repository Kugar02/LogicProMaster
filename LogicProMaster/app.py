import streamlit as st
import pandas as pd
from engine import run_monte_carlo_with_kelly, build_logical_columns, get_derived_road
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
if 'bet_strategy' not in st.session_state:
    st.session_state.bet_strategy = "半凱利 (Half-Kelly Dynamic)"
if 'base_unit' not in st.session_state:
    st.session_state.base_unit = 100.0
if 'stop_loss' not in st.session_state:
    st.session_state.stop_loss = 2000.0
if 'target_profit' not in st.session_state:
    st.session_state.target_profit = 3000.0

st.title("🎲 Quantum Baccarat Dynamic OS")

# ==============================================================================
# 2. 資金管理與策略控制面板 (開牌紀錄上方)
# ==============================================================================
st.subheader("⚙️ 資金管理與策略控制")

col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)

with col_s1:
    st.session_state.bankroll = st.number_input(
        "💰 當前總資金 ($)", 
        value=float(st.session_state.bankroll), 
        step=100.0, 
        key="input_bankroll"
    )

with col_s2:
    st.session_state.bet_strategy = st.selectbox(
        "🎰 資金管理策略",
        [
            "半凱利 (Half-Kelly Dynamic)",
            "固定平注 (Flat Betting)",
            "馬丁格爾倍投 (Martingale)",
            "勝進直纜 (1-2-4-8)",
            "自訂固定百分比 (Fixed %)"
        ],
        index=0,
        key="input_strat"
    )

with col_s3:
    st.session_state.base_unit = st.number_input(
        "💵 基礎注碼/每注基碼 ($)", 
        value=float(st.session_state.base_unit), 
        step=50.0, 
        key="input_base_unit"
    )

with col_s4:
    st.session_state.stop_loss = st.number_input(
        "🛑 止損門檻 ($)", 
        value=float(st.session_state.stop_loss), 
        step=500.0, 
        key="input_stop_loss"
    )

with col_s5:
    st.session_state.target_profit = st.number_input(
        "🎯 止盈目標 ($)", 
        value=float(st.session_state.target_profit), 
        step=500.0, 
        key="input_target_profit"
    )

col_p1, col_p2, col_p3 = st.columns([2, 1.5, 1.5])

with col_p1:
    profit = st.session_state.total_profit
    profit_color = "green" if profit >= 0 else "red"
    st.markdown(f"**當前累計盈虧：** <span style='color:{profit_color};font-size:18px;font-weight:bold;'>${profit:+.2f}</span>", unsafe_allow_html=True)
    if profit <= -st.session_state.stop_loss and st.session_state.stop_loss > 0:
        st.error("🚨 警告：已觸發止損門檻，建議停止下注離場避險！")
    elif profit >= st.session_state.target_profit and st.session_state.target_profit > 0:
        st.success("🎉 恭喜：已達到止盈目標，建議獲利結算！")

with col_p2:
    if st.button("🔄 重置資金與盈虧", use_container_width=True):
        st.session_state.total_profit = 0.0
        st.rerun()

with col_p3:
    if st.button("📦 備份當前牌靴至 KUGAR", use_container_width=True):
        with st.spinner("正在上傳至 Google Drive..."):
            success, result = upload_shoe_to_kugar(
                shoe_history=st.session_state.history_list,
                session_stats={
                    "bankroll": st.session_state.bankroll,
                    "total_profit": st.session_state.total_profit,
                    "strategy": st.session_state.bet_strategy
                }
            )
            if success:
                st.success("✅ 保存成功！")
                st.markdown(f"[🔗 在 Drive 查看檔案]({result})")
            else:
                st.error(result)

st.markdown("---")

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
    
    # 注碼策略換算
    win_p = max(final_b_pct, final_p_pct) / 100.0
    edge = (win_p - (1 - win_p))
    
    if "觀望" in recommend:
        suggested_bet = 0.0
        strat_note = "⏸️ 訊號混沌，暫不建議投注"
    else:
        strat = st.session_state.bet_strategy
        base_u = st.session_state.base_unit
        
        if strat == "半凱利 (Half-Kelly Dynamic)":
            kelly_f = max(0.0, min(0.08, (edge / 1.0) * 0.5))
            suggested_bet = round(st.session_state.bankroll * kelly_f, 0)
            strat_note = f"半凱利比例: {kelly_f*100:.1f}%"
        elif strat == "固定平注 (Flat Betting)":
            suggested_bet = base_u
            strat_note = f"固定平注 1 基碼 (${base_u:.0f})"
        elif strat == "馬丁格爾倍投 (Martingale)":
            suggested_bet = base_u * (2 ** consec_losses)
            strat_note = f"馬丁格爾倍投 (連虧 {consec_losses} 手，{2**consec_losses} 倍)"
        elif strat == "勝進直纜 (1-2-4-8)":
            suggested_bet = base_u
            strat_note = "勝進纜模式"
        else:
            suggested_bet = round(st.session_state.bankroll * 0.02, 0)
            strat_note = "自訂 2% 風控下注"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 莊家歸一化權重", f"{final_b_pct}%")
    m2.metric("🔵 閒家歸一化權重", f"{final_p_pct}%")
    m3.metric("🎯 訊號可信度", f"{confidence_pct}%")
    m4.metric(f"💵 推薦注碼 ({st.session_state.bet_strategy.split()[0]})", f"${suggested_bet:.0f}", help=strat_note)

    if is_break_active:
        st.warning(f"⚠️ 觸發智能防禦反打機制 (連續未命中: {consec_losses} 手)")
    if is_resonance:
        st.success("🔥 下三路三路極致共振爆發點！")

    st.caption(markov_status)

    # 4 大核心路單診斷
    st.markdown("### 🔍 4 大核心路單獨立診斷")
    r_cols = st.columns(4)
    for idx, (rk, rv) in enumerate(four_roads_data.items()):
        with r_cols[idx]:
            st.markdown(f"**{rv['name']}**")
            st.write(rv['status'])
            if rv['details']:
                st.caption(" • " + "\n • ".join(rv['details']))

# ==============================================================================
# 5. 線上娛樂城標準 5 路視覺化路紙 + 莊閒問路 + 繁體統計
# ==============================================================================
st.markdown("---")
st.markdown("### 📜 線上娛樂城標準五路看板 (標準 Baccarat Road Paper)")

# 莊閒問路運算函式
def get_ask_road_icons(history_seq):
    # 莊問路 (+B)
    cols_b = build_logical_columns(history_seq + ['B'])
    d_b1 = get_derived_road(cols_b, 1)
    d_b2 = get_derived_road(cols_b, 2)
    d_b3 = get_derived_road(cols_b, 3)

    # 閒問路 (+P)
    cols_p = build_logical_columns(history_seq + ['P'])
    d_p1 = get_derived_road(cols_p, 1)
    d_p2 = get_derived_road(cols_p, 2)
    d_p3 = get_derived_road(cols_p, 3)

    def sym(val, road_type):
        if not val:
            return "—"
        if road_type == "eye":
            return "<span style='color:#E74C3C;font-weight:bold;font-size:18px;'>⭕</span>" if val == 'Red' else "<span style='color:#3498DB;font-weight:bold;font-size:18px;'>⭕</span>"
        elif road_type == "small":
            return "<span style='color:#E74C3C;font-size:18px;'>🔴</span>" if val == 'Red' else "<span style='color:#3498DB;font-size:18px;'>🔵</span>"
        else: # roach
            return "<span style='color:#E74C3C;font-weight:bold;font-size:20px;'>╱</span>" if val == 'Red' else "<span style='color:#3498DB;font-weight:bold;font-size:20px;'>╱</span>"

    return {
        'B': (sym(d_b1[-1] if d_b1 else None, "eye"), sym(d_b2[-1] if d_b2 else None, "small"), sym(d_b3[-1] if d_b3 else None, "roach")),
        'P': (sym(d_p1[-1] if d_p1 else None, "eye"), sym(d_p2[-1] if d_p2 else None, "small"), sym(d_p3[-1] if d_p3 else None, "roach"))
    }

ask_res = get_ask_road_icons(history)

# 頂部綜合問路與數據統計列
ask_col1, ask_col2 = st.columns([1, 1])

with ask_col1:
    st.markdown(
        f"""
        <div style="background-color:#F8F9F9;border:1px solid #D5D8DC;border-radius:8px;padding:10px;text-align:center;">
            <span style="font-weight:bold;font-size:16px;color:#2C3E50;">📊 統計數據：</span>
            <span style="background-color:#E74C3C;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;margin-right:5px;">莊 {b_count}</span>
            <span style="background-color:#3498DB;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;margin-right:5px;">閒 {p_count}</span>
            <span style="background-color:#2ECC71;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;margin-right:5px;">和 {t_count}</span>
            <span style="background-color:#7F8C8D;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;">總 {total_hands}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

with ask_col2:
    st.markdown(
        f"""
        <div style="background-color:#F8F9F9;border:1px solid #D5D8DC;border-radius:8px;padding:8px;display:flex;justify-content:space-around;align-items:center;">
            <div style="background-color:#E74C3C;color:white;padding:4px 12px;border-radius:6px;font-weight:bold;">
                莊問路: {ask_res['B'][0]} {ask_res['B'][1]} {ask_res['B'][2]}
            </div>
            <div style="background-color:#3498DB;color:white;padding:4px 12px;border-radius:6px;font-weight:bold;">
                閒問路: {ask_res['P'][0]} {ask_res['P'][1]} {ask_res['P'][2]}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write("")

# 5 路標籤頁模式與綜合矩陣顯示
tab_all, tab_bead, tab_big, tab_eye, tab_small, tab_roach = st.tabs([
    "🖥️ 綜合線上五路看板",
    "🔴🔵 珠盤路 (Bead Plate)",
    "📊 大路 (Big Road)",
    "⭕ 大眼仔路 (Big Eye)",
    "🔴 小路 (Small Road)",
    "╱ 曱甴路 (Cockroach Road)"
])

def build_derived_columns(derived_list):
    cols, current_col, last_val = [], [], None
    for val in derived_list:
        if val != last_val:
            if current_col:
                cols.append(current_col)
            current_col = [val]
            last_val = val
        else:
            current_col.append(val)
    if current_col:
        cols.append(current_col)
    return cols

# --- 1. 綜合線上五路看板 ---
with tab_all:
    col_left, col_right = st.columns([1, 2])
    
    # 左側：珠盤路
    with col_left:
        st.markdown("**🔴🔵 珠盤路**")
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

        html_bead = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
        for row in bead_rows:
            html_bead += "<tr style='height:32px;'>"
            for cell in row[-10:]: # 顯示最新 10 列
                html_bead += f"<td style='border:1px solid #CBD5E1;'>{cell}</td>"
            html_bead += "</tr>"
        html_bead += "</table>"
        st.markdown(html_bead, unsafe_allow_html=True)

    # 右側：大路與下三路
    with col_right:
        st.markdown("**📊 大路**")
        big_cols = build_logical_columns(history)
        disp_big = big_cols[-15:]
        if disp_big:
            max_r = max(len(c) for c in disp_big)
            grid = [["" for _ in range(len(disp_big))] for _ in range(max_r)]
            for c_idx, col_data in enumerate(disp_big):
                for r_idx, val in enumerate(col_data):
                    if val == 'B':
                        grid[r_idx][c_idx] = "<span style='color:#E74C3C;font-weight:bold;'>🔴</span>"
                    else:
                        grid[r_idx][c_idx] = "<span style='color:#3498DB;font-weight:bold;'>🔵</span>"

            big_html = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
            for row in grid:
                big_html += "<tr style='height:28px;'>"
                for cell in row:
                    big_html += f"<td style='border:1px solid #CBD5E1;'>{cell}</td>"
                big_html += "</tr>"
            big_html += "</table>"
            st.markdown(big_html, unsafe_allow_html=True)
        else:
            st.info("大路未開出")

# --- 2. 珠盤路 (獨立全頁) ---
with tab_bead:
    bead_rows = [[] for _ in range(6)]
    for idx, item in enumerate(history):
        r = idx % 6
        if item == 'B':
            badge = "<span style='background-color:#E74C3C;color:white;padding:3px 10px;border-radius:50%;font-weight:bold;'>莊</span>"
        elif item == 'P':
            badge = "<span style='background-color:#3498DB;color:white;padding:3px 10px;border-radius:50%;font-weight:bold;'>閒</span>"
        else:
            badge = "<span style='background-color:#2ECC71;color:white;padding:3px 10px;border-radius:50%;font-weight:bold;'>和</span>"
        bead_rows[r].append(badge)

    html_table = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
    for row in bead_rows:
        html_table += "<tr style='height:36px;'>"
        for cell in row:
            html_table += f"<td style='border:1px solid #333;'>{cell}</td>"
        html_table += "</tr>"
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)

# --- 3. 大路 ---
with tab_big:
    big_cols = build_logical_columns(history)
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
    else:
        st.info("大路未開出")

# 通用渲染下三路矩陣
def render_derived_road_matrix(k, road_name, symbol_red, symbol_blue):
    logical_cols = build_logical_columns(history)
    derived = get_derived_road(logical_cols, k)
    if not derived:
        st.info(f"{road_name}尚未開出 (需大路達到足夠欄位)")
        return
    d_cols = build_derived_columns(derived)
    disp = d_cols[-20:]
    if disp:
        max_r = max(len(c) for c in disp)
        grid = [["" for _ in range(len(disp))] for _ in range(max_r)]
        for c_idx, col_data in enumerate(disp):
            for r_idx, val in enumerate(col_data):
                if val == 'Red':
                    grid[r_idx][c_idx] = f"<span style='color:#E74C3C;font-weight:bold;'>{symbol_red}</span>"
                else:
                    grid[r_idx][c_idx] = f"<span style='color:#3498DB;font-weight:bold;'>{symbol_blue}</span>"

        html = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
        for row in grid:
            html += "<tr style='height:30px;'>"
            for cell in row:
                html += f"<td style='border:1px solid #444;'>{cell}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

# --- 4. 大眼仔路 ---
with tab_eye:
    render_derived_road_matrix(1, "大眼仔路", "⭕", "⭕")

# --- 5. 小路 ---
with tab_small:
    render_derived_road_matrix(2, "小路", "🔴", "🔵")

# --- 6. 曱甴路 ---
with tab_roach:
    render_derived_road_matrix(3, "曱甴路", "╱", "╱")

st.markdown("---")
st.write(f"📊 當前歷史記錄 (共 {total_hands} 局): ", " ".join(history[-30:]))
