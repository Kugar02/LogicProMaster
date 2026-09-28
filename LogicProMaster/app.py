import streamlit as st
import pandas as pd
from engine import run_monte_carlo_with_kelly, build_logical_columns, get_derived_road
from drive_logger import upload_shoe_to_kugar

st.set_page_config(page_title="Quantum Baccarat Dynamic OS", layout="wide", page_icon="🎲")

# ==============================================================================
# 1. 防禦性 Session State 初始化與 AI 勝負追蹤
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
# --- 新增：AI 勝負與動態結算追蹤 ---
if 'ai_wins' not in st.session_state:
    st.session_state.ai_wins = 0
if 'ai_losses' not in st.session_state:
    st.session_state.ai_losses = 0
if 'next_bet' not in st.session_state:
    st.session_state.next_bet = {'target': None, 'amount': 0.0}

st.title("🎲 Quantum Baccarat Dynamic OS")

# ==============================================================================
# 2. 資金管理與策略控制面板
# ==============================================================================
st.subheader("⚙️ 資金管理與策略控制")

col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
with col_s1:
    st.session_state.bankroll = st.number_input("💰 當前總資金 ($)", value=float(st.session_state.bankroll), step=100.0)
with col_s2:
    st.session_state.bet_strategy = st.selectbox(
        "🎰 資金管理策略",
        ["半凱利 (Half-Kelly Dynamic)", "固定平注 (Flat Betting)", "馬丁格爾倍投 (Martingale)", "勝進直纜 (1-2-4-8)", "自訂固定百分比 (Fixed %)"],
        index=0
    )
with col_s3:
    st.session_state.base_unit = st.number_input("💵 基碼 ($)", value=float(st.session_state.base_unit), step=50.0)
with col_s4:
    st.session_state.stop_loss = st.number_input("🛑 止損門檻 ($)", value=float(st.session_state.stop_loss), step=500.0)
with col_s5:
    st.session_state.target_profit = st.number_input("🎯 止盈目標 ($)", value=float(st.session_state.target_profit), step=500.0)

# ==============================================================================
# 3. 動態結算輸入邏輯 (解決問題一：累計盈虧與勝率計算)
# ==============================================================================
def process_new_result(res):
    nb = st.session_state.next_bet
    tgt = nb['target']
    amt = nb['amount']
    
    # 計算盈虧與 AI 勝負 (和局不扣本金)
    if res in ['B', 'P'] and tgt:
        if res == tgt:
            st.session_state.ai_wins += 1
            profit = amt * 0.95 if res == 'B' else amt # 莊贏扣 5% 水錢
            st.session_state.total_profit += profit
        else:
            st.session_state.ai_losses += 1
            st.session_state.total_profit -= amt
            
    st.session_state.history_list.append(res)
    st.session_state.next_bet = {'target': None, 'amount': 0.0} # 重置，等待引擎重新計算

st.subheader("🎛️ 開牌紀錄與快捷輸入")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🔴 開莊 (B)", use_container_width=True):
        process_new_result('B')
        st.rerun()
with c2:
    if st.button("🔵 開閒 (P)", use_container_width=True):
        process_new_result('P')
        st.rerun()
with c3:
    if st.button("🟢 開和 (T)", use_container_width=True):
        process_new_result('T')
        st.rerun()
with c4:
    if st.button("↩️ 撤銷上一手", use_container_width=True):
        if st.session_state.history_list:
            st.session_state.history_list.pop()
            # 撤銷時不作複雜的盈虧回溯，建議用重置
            st.rerun()

col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
with col_b1:
    batch_input = st.text_input("📝 批量輸入歷史賽果 (例如: BBPPBPT)", label_visibility="collapsed", placeholder="批量輸入賽果 (例如: BBPPBPT)")
with col_b2:
    if st.button("📥 一鍵載入", use_container_width=True):
        if batch_input:
            st.session_state.ai_wins, st.session_state.ai_losses, st.session_state.total_profit = 0, 0, 0.0
            st.session_state.history_list = [x.upper() for x in batch_input.strip() if x.upper() in ['B', 'P', 'T']]
            st.rerun()
with col_b3:
    if st.button("🗑️ 清空重置 (新靴)", use_container_width=True):
        if len(st.session_state.history_list) > 0:
            upload_shoe_to_kugar(st.session_state.history_list, session_stats={"profit": st.session_state.total_profit})
        st.session_state.history_list, st.session_state.ai_targets = [], []
        st.session_state.ai_wins, st.session_state.ai_losses, st.session_state.total_profit = 0, 0, 0.0
        st.rerun()

# ==============================================================================
# 4. 核心推理引擎計算與 AI 決策顯示
# ==============================================================================
history = st.session_state.history_list
b_count, p_count, t_count = history.count('B'), history.count('P'), history.count('T')
total_hands = len(history)

if total_hands > 0:
    avg_tc, final_b_pct, final_p_pct, actual_t_ratio, recommend, four_roads_data, is_break_active, consec_losses, markov_status, is_resonance, confidence_pct = run_monte_carlo_with_kelly(
        b_count, p_count, t_count, bankroll=st.session_state.bankroll, sim_count=0, history_list=history, ai_targets=st.session_state.ai_targets
    )

    # ------------------ 注碼策略換算 ------------------
    win_p = max(final_b_pct, final_p_pct) / 100.0
    edge = (win_p - (1 - win_p))
    
    if "觀望" in recommend:
        suggested_bet, strat_note, next_tgt = 0.0, "⏸️ 訊號混沌，建議觀望", None
    else:
        next_tgt = 'B' if "【莊】" in recommend else ('P' if "【閒】" in recommend else None)
        strat, base_u = st.session_state.bet_strategy, st.session_state.base_unit
        
        if strat == "半凱利 (Half-Kelly Dynamic)":
            kelly_f = max(0.0, min(0.08, (edge / 1.0) * 0.5))
            suggested_bet = round(st.session_state.bankroll * kelly_f, 0)
            strat_note = f"半凱利比例: {kelly_f*100:.1f}%"
        elif strat == "固定平注 (Flat Betting)":
            suggested_bet = base_u
            strat_note = f"固定平注 1 基碼"
        elif strat == "馬丁格爾倍投 (Martingale)":
            suggested_bet = base_u * (2 ** consec_losses)
            strat_note = f"連虧 {consec_losses} 手倍投"
        elif strat == "勝進直纜 (1-2-4-8)":
            suggested_bet = base_u
            strat_note = "勝進纜模式"
        else:
            suggested_bet = round(st.session_state.bankroll * 0.02, 0)
            strat_note = "2% 風控下注"

    # 將下一手的建議寫入 Session State 等待驗證
    st.session_state.next_bet = {'target': next_tgt, 'amount': suggested_bet}

    st.markdown("---")
    
    # ------------------ 統計與建議面板 ------------------
    total_ai = st.session_state.ai_wins + st.session_state.ai_losses
    ai_rate = (st.session_state.ai_wins / total_ai * 100) if total_ai > 0 else 0.0
    profit = st.session_state.total_profit
    profit_color = "#2ECC71" if profit >= 0 else "#E74C3C"

    st.markdown(f"""
    <div style="background-color:#1E2129; border: 1px solid #3A3F4B; border-radius:10px; padding:20px; color:white;">
        <h2 style="margin-top:0; color:#F1C40F;">🎯 最終權重建議：{recommend}</h2>
        <div style="display:flex; justify-content:space-between; flex-wrap:wrap; font-size:18px;">
            <div>💰 <b>累計盈虧：</b> <span style="color:{profit_color}; font-weight:bold; font-size:24px;">${profit:+.2f}</span></div>
            <div>💵 <b>推薦下注：</b> <span style="color:#3498DB; font-weight:bold; font-size:24px;">${suggested_bet:.0f}</span> <span style="font-size:14px; color:#95A5A6;">({strat_note})</span></div>
            <div>🏆 <b>AI 勝率統計：</b> {st.session_state.ai_wins}勝 {st.session_state.ai_losses}負 <span style="color:#E67E22; font-weight:bold;">({ai_rate:.1f}%)</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_break_active: st.warning(f"⚠️ 觸發智能防禦反打機制 (連續未命中: {consec_losses} 手)")
    if is_resonance: st.success("🔥 下三路三路極致共振爆發點！")
    st.caption(markov_status)

# ==============================================================================
# 5. 線上娛樂城標準 5 路一體化看板 (解決問題二：一眼睇晒格網排版)
# ==============================================================================
st.markdown("---")
st.markdown("### 🖥️ 綜合線上五路看板 (標準 Casino Grid)")

def get_ask_road_icons(history_seq):
    cols_b = build_logical_columns(history_seq + ['B'])
    d_b1, d_b2, d_b3 = get_derived_road(cols_b, 1), get_derived_road(cols_b, 2), get_derived_road(cols_b, 3)
    cols_p = build_logical_columns(history_seq + ['P'])
    d_p1, d_p2, d_p3 = get_derived_road(cols_p, 1), get_derived_road(cols_p, 2), get_derived_road(cols_p, 3)

    def sym(val, r_type):
        if not val: return "—"
        if r_type == "eye": return "⭕" if val == 'Red' else "🔵" # HTML style simplified for readability
        elif r_type == "small": return "🔴" if val == 'Red' else "🔵"
        else: return "╱" if val == 'Red' else "＼"

    return {
        'B': (sym(d_b1[-1] if d_b1 else None, "eye"), sym(d_b2[-1] if d_b2 else None, "small"), sym(d_b3[-1] if d_b3 else None, "roach")),
        'P': (sym(d_p1[-1] if d_p1 else None, "eye"), sym(d_p2[-1] if d_p2 else None, "small"), sym(d_p3[-1] if d_p3 else None, "roach"))
    }

ask = get_ask_road_icons(history)

# 頂部問路列
st.markdown(f"""
<div style="background-color:#F8F9F9;border:1px solid #D5D8DC;border-radius:6px;padding:8px;display:flex;justify-content:space-between;align-items:center; margin-bottom:10px;">
    <div>
        <span style="font-weight:bold;font-size:16px;">📊 統計：</span>
        <span style="background:#E74C3C;color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">莊 {b_count}</span>
        <span style="background:#3498DB;color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">閒 {p_count}</span>
        <span style="background:#2ECC71;color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">和 {t_count}</span>
        <span style="background:#7F8C8D;color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">總 {total_hands}</span>
    </div>
    <div style="display:flex; gap:15px;">
        <div style="background:#E74C3C;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;">莊問路: {ask['B'][0]} {ask['B'][1]} {ask['B'][2]}</div>
        <div style="background:#3498DB;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;">閒問路: {ask['P'][0]} {ask['P'][1]} {ask['P'][2]}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 佈局：左邊 1/4 是珠盤路，右邊 3/4 是大路及下三路
col_bead, col_roads = st.columns([1, 3])

# --- 左側：珠盤路 ---
with col_bead:
    bead_rows = [[] for _ in range(6)]
    for idx, item in enumerate(history):
        r = idx % 6
        if item == 'B': badge = "<span style='background-color:#E74C3C;color:white;display:inline-block;width:24px;height:24px;line-height:24px;border-radius:50%;font-weight:bold;font-size:12px;'>莊</span>"
        elif item == 'P': badge = "<span style='background-color:#3498DB;color:white;display:inline-block;width:24px;height:24px;line-height:24px;border-radius:50%;font-weight:bold;font-size:12px;'>閒</span>"
        else: badge = "<span style='background-color:#2ECC71;color:white;display:inline-block;width:24px;height:24px;line-height:24px;border-radius:50%;font-weight:bold;font-size:12px;'>和</span>"
        bead_rows[r].append(badge)

    html_bead = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
    for row in bead_rows:
        html_bead += "<tr style='height:36px;'>"
        for cell in row[-8:]: # 顯示最新 8 欄確保排版不溢出
            html_bead += f"<td style='border:1px solid #CBD5E1; padding:2px;'>{cell}</td>"
        # 補齊空白格
        for _ in range(8 - len(row[-8:])):
            html_bead += "<td style='border:1px solid #CBD5E1;'></td>"
        html_bead += "</tr>"
    html_bead += "</table>"
    st.markdown(html_bead, unsafe_allow_html=True)

# --- 右側：大路 + 下三路 網格佈局 ---
with col_roads:
    # 1. 大路 (上半部)
    big_cols = build_logical_columns(history)
    disp_big = big_cols[-20:]
    max_r = 6 # 固定至少 6 行高度
    if disp_big: max_r = max(6, max(len(c) for c in disp_big))
    
    grid_big = [["" for _ in range(20)] for _ in range(max_r)]
    for c_idx, col_data in enumerate(disp_big):
        for r_idx, val in enumerate(col_data):
            if r_idx < max_r and c_idx < 20:
                grid_big[r_idx][c_idx] = "🔴" if val == 'B' else "🔵"

    big_html = "<table style='width:100%;text-align:center;border-collapse:collapse; margin-bottom:10px;'>"
    for row in grid_big:
        big_html += "<tr style='height:30px;'>"
        for cell in row:
            big_html += f"<td style='border:1px solid #CBD5E1; font-size:14px;'>{cell}</td>"
        big_html += "</tr>"
    big_html += "</table>"
    st.markdown(big_html, unsafe_allow_html=True)

    # 2. 下三路 (下半部，平行 3 欄排列)
    c_eye, c_small, c_roach = st.columns(3)
    
    def render_derived(k, symbol_red, symbol_blue):
        derived = get_derived_road(build_logical_columns(history), k)
        if not derived: return "<div style='color:#999; font-size:12px; text-align:center;'>未成路</div>"
        
        d_cols, cur, last = [], [], None
        for v in derived:
            if v != last:
                if cur: d_cols.append(cur)
                cur, last = [v], v
            else: cur.append(v)
        if cur: d_cols.append(cur)
        
        disp = d_cols[-12:] # 顯示最新 12 欄
        g = [["" for _ in range(12)] for _ in range(6)]
        for c_idx, col_data in enumerate(disp):
            for r_idx, val in enumerate(col_data):
                if r_idx < 6 and c_idx < 12:
                    g[r_idx][c_idx] = symbol_red if val == 'Red' else symbol_blue
                    
        h = "<table style='width:100%;text-align:center;border-collapse:collapse;'>"
        for row in g:
            h += "<tr style='height:20px;'>"
            for cell in row:
                h += f"<td style='border:1px solid #CBD5E1; font-size:10px; padding:0;'>{cell}</td>"
            h += "</tr>"
        h += "</table>"
        return h

    with c_eye:
        st.markdown("<div style='font-size:14px; font-weight:bold; margin-bottom:5px;'>⭕ 大眼仔路</div>", unsafe_allow_html=True)
        st.markdown(render_derived(1, "⭕", "⭕"), unsafe_allow_html=True)
    with c_small:
        st.markdown("<div style='font-size:14px; font-weight:bold; margin-bottom:5px;'>🔴 小路</div>", unsafe_allow_html=True)
        st.markdown(render_derived(2, "🔴", "🔵"), unsafe_allow_html=True)
    with c_roach:
        st.markdown("<div style='font-size:14px; font-weight:bold; margin-bottom:5px;'>╱ 曱甴路</div>", unsafe_allow_html=True)
        st.markdown(render_derived(3, "╱", "＼"), unsafe_allow_html=True)

st.markdown("---")
st.write(f"📊 當前歷史記錄 (共 {total_hands} 局): ", " ".join(history[-30:]))
