import streamlit as st
import pandas as pd

# 嘗試載入計算引擎
try:
    from engine import run_monte_carlo_with_kelly
except ImportError:
    run_monte_carlo_with_kelly = None

# ================= 1. 系統全域設定 =================
st.set_page_config(page_title="Quantum Baccarat OS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 98% !important; }
        .stButton>button { height: 45px; font-size: 18px; font-weight: bold; border-radius: 8px; }
        .road-container { background: white; padding: 5px; border-radius: 8px; overflow-x: auto; margin-bottom: 15px; border: 1px solid #ddd;}
        .ask-road-box { background: #1e1e1e; border-radius: 8px; padding: 10px; text-align: center; color: white; border: 1px solid #444;}
        .ask-icons { display: flex; justify-content: center; gap: 15px; margin-top: 10px; }
        .stat-box { background: #262730; padding: 15px; border-radius: 8px; border: 1px solid #555; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 初始化資料庫 (加入 AI 歷史推薦紀錄)
if 'history' not in st.session_state: st.session_state.history = []
if 'ai_targets' not in st.session_state: st.session_state.ai_targets = []
if 'bankroll' not in st.session_state: st.session_state.bankroll = 10000

# ================= 2. 頂部策略與資金控制台 =================
st.markdown("### ⚙️ 資金管理與策略設定")
c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
st.session_state.bankroll = c1.number_input("💰 初始總本金 ($)", min_value=100, value=st.session_state.bankroll, step=500)
st.session_state.base_unit = c2.number_input("💵 基礎單位注碼 ($)", min_value=10, value=100, step=10)
st.session_state.strategy = c3.selectbox("📈 選擇下注策略", ["信號強弱 (1-2-3)", "斐波那契 (Fibonacci)", "馬丁格爾 (Martingale)"])

if c4.button("🗑️ 清空重置 (新靴)", use_container_width=True): 
    st.session_state.history = []
    st.session_state.ai_targets = []
    st.rerun()

# --- 動態重建策略狀態 (處理復原與歷史統計) ---
fibo_idx = 0
martingale_mult = 1
total_bets, wins, losses, pnl = 0, 0, 0, 0.0

for tgt, actual in zip(st.session_state.ai_targets, st.session_state.history):
    if tgt and tgt['target']:
        total_bets += 1
        amt = tgt['amount']
        if actual == 'T': pass
        else:
            is_win = (tgt['target'] == actual)
            if is_win:
                wins += 1
                pnl += (amt * 0.95) if actual == 'B' else amt
                fibo_idx = max(0, fibo_idx - 2)
                martingale_mult = 1
            else:
                losses += 1
                pnl -= amt
                fibo_idx += 1
                martingale_mult *= 2

# ================= 3. 實時開牌輸入區 =================
st.markdown("### 🎛️ 開牌輸入")
btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

def record_hand(result):
    st.session_state.ai_targets.append(st.session_state.get('pending_target', None))
    st.session_state.history.append(result)
    st.rerun()

if btn_col1.button("🔴 開莊 (B)", use_container_width=True): record_hand('B')
if btn_col2.button("🔵 開閒 (P)", use_container_width=True): record_hand('P')
if btn_col3.button("🟢 開和 (T)", use_container_width=True): record_hand('T')
if btn_col4.button("↩️ 撤銷上一手", use_container_width=True): 
    if st.session_state.history: 
        st.session_state.history.pop()
        st.session_state.ai_targets.pop()
    st.rerun()

st.markdown("---")

# ================= 4. AI 分析核心與下注指令 =================
st.markdown("### 🧠 AI 決策與策略統計")

total_hands = len(st.session_state.history)
b_count = st.session_state.history.count('B')
p_count = st.session_state.history.count('P')
t_count = st.session_state.history.count('T')

st.session_state.pending_target = None

if total_hands > 0 and run_monte_carlo_with_kelly:
    # 忽略原有的凱利回傳值
    avg_tc, b_prob, p_prob, t_prob, recommend, _, _ = run_monte_carlo_with_kelly(
        b_count, p_count, t_count, bankroll=st.session_state.bankroll, sim_count=10000
    )
    
    # 判斷 AI 方向
    target = 'B' if "莊" in recommend else 'P' if "閒" in recommend else None
    bet_amount = 0
    
    if target:
        if st.session_state.strategy == "信號強弱 (1-2-3)":
            tc_abs = abs(avg_tc)
            if tc_abs >= 5: bet_amount = st.session_state.base_unit * 3
            elif tc_abs >= 2: bet_amount = st.session_state.base_unit * 2
            else: bet_amount = st.session_state.base_unit
        
        elif st.session_state.strategy == "斐波那契 (Fibonacci)":
            fibo_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
            idx = min(fibo_idx, len(fibo_seq)-1)
            bet_amount = st.session_state.base_unit * fibo_seq[idx]
            
        elif st.session_state.strategy == "馬丁格爾 (Martingale)":
            bet_amount = st.session_state.base_unit * martingale_mult

        st.session_state.pending_target = {'target': target, 'amount': bet_amount}
        st.success(f"🔥 **下局目標：買【{'莊' if target == 'B' else '閒'}】** ｜ 💵 策略注碼：**${bet_amount}**")
    else:
        st.warning(f"🛡️ **防禦信號：當前無明顯優勢，建議觀望停注。**")

    # 顯示策略統計面板
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("策略歷史下注", f"{total_bets} 局", f"勝 {wins} / 負 {losses}")
    sm2.metric("AI 策略勝率", f"{(wins/total_bets*100):.1f}%" if total_bets > 0 else "0.0%")
    sm3.metric("策略累計損益", f"${pnl:.2f}", delta=f"{pnl:.2f}")
    sm4.metric("目前總資產", f"${st.session_state.bankroll + pnl:.2f}")


# ================= 5. 下三路核心演算法 =================
def build_logical_columns(history):
    cols, current_col, last_res = [], [], None
    for res in history:
        if res == 'T': continue
        if res != last_res:
            if current_col: cols.append(current_col)
            current_col = [res]; last_res = res
        else: current_col.append(res)
    if current_col: cols.append(current_col)
    return cols

def get_derived_road(cols, k):
    derived = []
    for c in range(1, len(cols)):
        for r in range(len(cols[c])):
            if c < k: continue
            if r == 0:
                if c < k + 1: continue
                derived.append('R' if len(cols[c-1]) == len(cols[c-1-k]) else 'B')
            else:
                len_ref = len(cols[c-k])
                if len_ref >= r + 1: derived.append('R')
                elif len_ref == r: derived.append('B')
                else: derived.append('R')
    return derived

def layout_road_matrix(data_list, rows=6):
    grid, curr_col, curr_row, start_col, last_val = {}, 0, 0, 0, None
    for item in data_list:
        if last_val is None:
            last_val = item; grid[(curr_col, curr_row)] = item
        elif item == last_val:
            curr_row += 1
            if curr_row >= rows or (curr_col, curr_row) in grid:
                curr_row -= 1; curr_col += 1
            grid[(curr_col, curr_row)] = item
        else:
            last_val = item; start_col += 1; curr_col = start_col
            while (curr_col, 0) in grid: curr_col += 1
            start_col = curr_col; curr_row = 0
            grid[(curr_col, curr_row)] = item
    return grid

def render_grid_html(grid, rows=6, cols=20, cell_size=20, road_type="big"):
    html = f'<table style="border-collapse: collapse; background: #fff; table-layout: fixed; margin: auto;">'
    for r in range(rows):
        html += '<tr>'
        for c in range(cols):
            cell = grid.get((c, r), None)
            content = ""
            if cell:
                val = cell['val'] if isinstance(cell, dict) else cell
                ties = cell.get('ties', 0) if isinstance(cell, dict) else 0
                color = "#e81123" if val in ['B', 'R'] else "#0078d7"
                
                if road_type == "bead":
                    bg = "#e81123" if val == 'B' else "#0078d7" if val == 'P' else "#2ca02c"
                    txt = "莊" if val == 'B' else "閒" if val == 'P' else "和"
                    content = f'<div style="width:20px;height:20px;background:{bg};color:white;border-radius:50%;font-size:10px;line-height:20px;text-align:center;margin:auto;font-weight:bold;">{txt}</div>'
                elif road_type == "big":
                    content = f'<div style="position:relative;width:14px;height:14px;border:2px solid {color};border-radius:50%;margin:auto;">'
                    if ties > 0: content += f'<div style="position:absolute;width:18px;height:2px;background:#2ca02c;transform:rotate(-45deg);top:6px;left:-4px;"></div>'
                    content += '</div>'
                elif road_type == "big_eye": content = f'<div style="width:10px;height:10px;border:2px solid {color};border-radius:50%;margin:auto;"></div>'
                elif road_type == "small": content = f'<div style="width:10px;height:10px;background:{color};border-radius:50%;margin:auto;"></div>'
                elif road_type == "roach": content = f'<div style="width:12px;height:2px;background:{color};transform:rotate(-45deg);margin:auto;margin-top:8px;"></div>'
            html += f'<td style="border: 1px solid #eee; width: {cell_size}px; height: {cell_size}px; text-align: center; vertical-align: middle;">{content}</td>'
        html += '</tr></table>'
    return html

# ================= 6. 渲染五大路單 =================
st.markdown("---")
st.markdown("### 📊 專業娛樂城路紙 (五路全開)")

big_road_list = []
for item in st.session_state.history:
    if item == 'T' and big_road_list: big_road_list[-1]['ties'] += 1
    elif item != 'T': big_road_list.append({'val': item, 'ties': 0})
        
logical_cols = build_logical_columns(st.session_state.history)

col_top1, col_top2 = st.columns([2, 5])
with col_top1:
    st.caption("珠盤路 (Bead Plate)")
    bead_grid = {(i // 6, i % 6): res for i, res in enumerate(st.session_state.history)}
    st.markdown(f'<div class="road-container">{render_grid_html(bead_grid, cols=12, cell_size=26, road_type="bead")}</div>', unsafe_allow_html=True)

with col_top2:
    st.caption("大路 (Big Road)")
    st.markdown(f'<div class="road-container">{render_grid_html(layout_road_matrix(big_road_list), cols=42, cell_size=26, road_type="big")}</div>', unsafe_allow_html=True)

st.caption("下三路 (Lower Three Roads: 大眼仔路 / 小路 / 曱甴路)")
col_bot1, col_bot2, col_bot3 = st.columns(3)
with col_bot1: st.markdown(f'<div class="road-container">{render_grid_html(layout_road_matrix(get_derived_road(logical_cols, 1)), cols=28, cell_size=18, road_type="big_eye")}</div>', unsafe_allow_html=True)
with col_bot2: st.markdown(f'<div class="road-container">{render_grid_html(layout_road_matrix(get_derived_road(logical_cols, 2)), cols=28, cell_size=18, road_type="small")}</div>', unsafe_allow_html=True)
with col_bot3: st.markdown(f'<div class="road-container">{render_grid_html(layout_road_matrix(get_derived_road(logical_cols, 3)), cols=28, cell_size=18, road_type="roach")}</div>', unsafe_allow_html=True)
