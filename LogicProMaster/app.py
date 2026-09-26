import streamlit as st
import pandas as pd

# 載入五層整合大腦 (engine.py)
try:
    from engine import run_monte_carlo_with_kelly
except ImportError:
    run_monte_carlo_with_kelly = None

# ================= 1. 頁面配置與高對比黑魂主題 CSS =================
st.set_page_config(page_title="Quantum Baccarat 100K OS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container { padding-top: 0.8rem !important; padding-bottom: 0rem !important; max-width: 98% !important; }
        .stButton>button { height: 48px; font-size: 18px; font-weight: bold; border-radius: 8px; }
        .ask-road-box { background: #16181f; border-radius: 8px; padding: 10px; text-align: center; color: white; border: 1px solid #2d313e;}
        .ask-icons { display: flex; justify-content: center; gap: 15px; margin-top: 6px; }
        .pattern-card { background: #1e2029; border: 1px solid #333644; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
        .weight-box { background: #0f1015; border: 2px solid #00ffcc; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state: st.session_state.history = []
if 'ai_targets' not in st.session_state: st.session_state.ai_targets = []
if 'bankroll' not in st.session_state: st.session_state.bankroll = 10000

# ================= 預先計算歷史統計與策略階段 =================
fibo_idx = 0
double_dragon_idx = 0
tumbler_unit = 1  # 不倒翁: 1 -> 2 -> 3 循環

total_bets, wins, losses, pnl = 0, 0, 0, 0.0

for tgt, actual in zip(st.session_state.ai_targets, st.session_state.history):
    if tgt and tgt['target'] and actual != 'T':
        total_bets += 1
        amt = tgt['amount']
        if tgt['target'] == actual:
            wins += 1
            pnl += (amt * 0.95) if actual == 'B' else amt
            
            # 獲勝時更新策略階段
            fibo_idx = max(0, fibo_idx - 2)
            double_dragon_idx = 0  # 雙頭龍贏局重置
            tumbler_unit = min(3, tumbler_unit + 1) if tumbler_unit < 3 else 1 # 不倒翁贏進 1->2->3，達3後重置
        else:
            losses += 1
            pnl -= amt
            
            # 落敗時更新策略階段
            fibo_idx += 1
            double_dragon_idx += 1 # 雙頭龍輸局進階 (1,1,2,2,4,4,8,8...)
            tumbler_unit = 1 # 不倒翁輸局保本重置為 1 注

# 預先運行 AI 預測以計算「當前下注注碼」
total_hands = len(st.session_state.history)
b_count = st.session_state.history.count('B')
p_count = st.session_state.history.count('P')
t_count = st.session_state.history.count('T')

current_bet = 0
target = None
recommend = "數據準備中..."
four_roads_data = {}
is_break_active = False
consec_losses = 0
final_b_pct, final_p_pct, actual_t_ratio = 45.8, 44.6, 9.5

if 'strategy' not in st.session_state: st.session_state.strategy = "信號強弱 (1-2-3)"
if 'base_unit' not in st.session_state: st.session_state.base_unit = 100

if total_hands > 0 and run_monte_carlo_with_kelly:
    avg_tc, final_b_pct, final_p_pct, actual_t_ratio, recommend, four_roads_data, is_break_active, consec_losses = run_monte_carlo_with_kelly(
        b_count, p_count, t_count, 
        bankroll=st.session_state.bankroll, 
        sim_count=100000, 
        history_list=st.session_state.history,
        ai_targets=st.session_state.ai_targets
    )
    
    target = 'B' if "莊" in recommend else 'P' if "閒" in recommend else None
    
    if target:
        if st.session_state.strategy == "信號強弱 (1-2-3)":
            diff = abs(final_b_pct - final_p_pct)
            if diff >= 10: current_bet = st.session_state.base_unit * 3
            elif diff >= 5: current_bet = st.session_state.base_unit * 2
            else: current_bet = st.session_state.base_unit
            
        elif st.session_state.strategy == "斐波那契 (Fibonacci)":
            fibo_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
            idx = min(fibo_idx, len(fibo_seq)-1)
            current_bet = st.session_state.base_unit * fibo_seq[idx]
            
        elif st.session_state.strategy == "雙頭龍":
            dd_seq = [1, 1, 2, 2, 4, 4, 8, 8, 16, 16, 32, 32]
            idx = min(double_dragon_idx, len(dd_seq)-1)
            current_bet = st.session_state.base_unit * dd_seq[idx]
            
        elif st.session_state.strategy == "不倒翁投注法":
            current_bet = st.session_state.base_unit * tumbler_unit

# ================= 2. 資金管理與注碼策略整合面板 =================
st.markdown("### ⚙️ 資金管理與注碼策略 (實時整合監控)")

c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
st.session_state.bankroll = c1.number_input("💰 初始總本金 ($)", min_value=100, value=st.session_state.bankroll, step=500)
st.session_state.base_unit = c2.number_input("💵 基礎注碼 ($)", min_value=10, value=st.session_state.base_unit, step=10)
st.session_state.strategy = c3.selectbox("📈 選擇注碼策略", ["信號強弱 (1-2-3)", "斐波那契 (Fibonacci)", "雙頭龍", "不倒翁投注法"])

if c4.button("🗑️ 清空重置 (新靴)", use_container_width=True): 
    st.session_state.history = []
    st.session_state.ai_targets = []
    st.rerun()

# 整合數據儀表板
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("💰 當前總資產", f"${st.session_state.bankroll + pnl:.2f}")
m2.metric("💵 當前建議注碼", f"${current_bet}" if current_bet > 0 else "$0 (觀望)")
m3.metric("📊 策略歷史下注", f"{total_bets} 局", f"勝 {wins} / 負 {losses}")
m4.metric("🎯 AI 策略勝率", f"{(wins/total_bets*100):.1f}%" if total_bets > 0 else "0.0%")
m5.metric("📈 策略累計損益", f"${pnl:.2f}", delta=f"{pnl:.2f}")

st.markdown("---")

# ================= 3. AI 預測建議與 4 大核心分析 =================
st.markdown("### 🧠 最終權重預測建議 (五層流水線 Pipeline)")

if total_hands > 0:
    st.markdown(f"""
    <div class="weight-box">
        <h2 style="margin:0; color:#00ffcc;">🎯 最終權重建議：{recommend}</h2>
        <p style="font-size: 18px; margin-top:8px;">
            <b>莊家歸一化權重：<span style="color:#ff4b4b;">{final_b_pct}%</span></b> ｜ 
            <b>閒家歸一化權重：<span style="color:#1f77b4;">{final_p_pct}%</span></b>
        </p>
        <small style="color:#aaa;">
            [流水線順序] 底座(莊45.86%|閒44.62%) ➔ 四核6特徵路型 ➔ 隱性修正(和率{actual_t_ratio}%) ➔ 100K殘牌MC ➔ 歸一化
        </small>
    </div>
    """, unsafe_allow_html=True)

    if is_break_active:
        st.error(f"🚨 **智能破路反打觸發**：連續 {consec_losses} 局正打爆路，四大路單權重已自動進行 Signal Inversion 反轉加權！")

if four_roads_data:
    st.markdown("#### 🔍 4 大核心路單獨立診斷 (各別跑滿六大特徵並取強者)")
    r_cols = st.columns(4)
    r_keys = list(four_roads_data.keys())
    for i, k in enumerate(r_keys):
        item = four_roads_data[k]
        color = "red" if item['dominant'] == 'B' else ("blue" if item['dominant'] == 'P' else "gray")
        with r_cols[i]:
            st.markdown(f"""
            <div class="pattern-card">
                <b>{item['name']}</b><br>
                <span style="color:{color}; font-size:13px; font-weight:bold;">{item['status']}</span><br>
                <small style="color:#aaa;">六特徵明細: {", ".join(item['details']) if item['details'] else '無明顯特徵'}</small>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ================= 4. 統合歷史數據介面 (開牌輸入 + 莊閒問路 + 專業路紙) =================
st.markdown("### 📜 歷史數據控制介面 (開牌紀錄 / 莊閒問路 / 五路圖表)")

# 4A. 開牌紀錄輸入區
st.markdown("##### 🎛️ 開牌紀錄與快捷輸入")
btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

def record_hand(result):
    st.session_state.ai_targets.append({'target': target, 'amount': current_bet} if target else None)
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

with st.expander("📝 批量輸入已開牌局 (快速補單)", expanded=False):
    batch_input = st.text_input("請輸入歷史賽果 (例如: BBPTP...)", placeholder="BBPTP...")
    if st.button("📥 一鍵載入歷史紀錄", use_container_width=True):
        cleaned = []
        for char in batch_input:
            if char in ['B', 'b', '莊', '庄']: cleaned.append('B')
            elif char in ['P', 'p', '閒', '闲']: cleaned.append('P')
            elif char in ['T', 't', '和']: cleaned.append('T')
        if cleaned:
            st.session_state.history.extend(cleaned)
            st.session_state.ai_targets.extend([None] * len(cleaned))
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# 4B. 莊閒問路 (整合在歷史數據介面內，緊貼開牌區)
st.markdown("##### 🔮 莊閒問路 (下局走向預測)")

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
                derived.append('Red' if len(cols[c-1]) == len(cols[c-1-k]) else 'Blue')
            else:
                len_ref = len(cols[c-k])
                if len_ref >= r + 1: derived.append('Red')
                elif len_ref == r: derived.append('Blue')
                else: derived.append('Red')
    return derived

def get_ask_road_symbols(history, test_val):
    temp_hist = history + [test_val]
    temp_cols = build_logical_columns(temp_hist)
    e = get_derived_road(temp_cols, 1)
    s = get_derived_road(temp_cols, 2)
    r = get_derived_road(temp_cols, 3)
    return (e[-1] if e else None, s[-1] if s else None, r[-1] if r else None)

ask_b = get_ask_road_symbols(st.session_state.history, 'B')
ask_p = get_ask_road_symbols(st.session_state.history, 'P')

def draw_ask_icon(val, r_type):
    if not val: return "<div style='width:20px; height:20px;'></div>"
    color = "#e81123" if val == 'Red' else "#0078d7"
    if r_type == 'eye': return f"<div style='width:16px;height:16px;border:3px solid {color};border-radius:50%;'></div>"
    if r_type == 'small': return f"<div style='width:16px;height:16px;background:{color};border-radius:50%;'></div>"
    if r_type == 'roach': return f"<div style='width:16px;height:4px;background:{color};transform:rotate(-45deg);margin-top:6px;'></div>"

col_ask_b, col_ask_p = st.columns(2)
with col_ask_b:
    st.markdown(f"""
    <div class="ask-road-box">
        <h5 style="color:#e81123; margin:0; padding-bottom: 3px;">🔴 莊問路 (Banker)</h5>
        <div class="ask-icons">
            {draw_ask_icon(ask_b[0], 'eye')} {draw_ask_icon(ask_b[1], 'small')} {draw_ask_icon(ask_b[2], 'roach')}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_ask_p:
    st.markdown(f"""
    <div class="ask-road-box">
        <h5 style="color:#0078d7; margin:0; padding-bottom: 3px;">🔵 閒問路 (Player)</h5>
        <div class="ask-icons">
            {draw_ask_icon(ask_p[0], 'eye')} {draw_ask_icon(ask_p[1], 'small')} {draw_ask_icon(ask_p[2], 'roach')}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 4C. 專業娛樂城路紙 (五路全開)
st.markdown("##### 📊 專業娛樂城路紙 (五路全開)")

def layout_road_matrix(data_list, rows=6):
    grid, curr_col, curr_row, start_col, last_val = {}, 0, 0, 0, None
    for item in data_list:
        val = item['val'] if isinstance(item, dict) else item
        if last_val is None:
            last_val = val; grid[(curr_col, curr_row)] = item
        elif val == last_val:
            curr_row += 1
            if curr_row >= rows or (curr_col, curr_row) in grid:
                curr_row -= 1; curr_col += 1
            grid[(curr_col, curr_row)] = item
        else:
            last_val = val; start_col += 1; curr_col = start_col
            while (curr_col, 0) in grid: curr_col += 1
            start_col = curr_col; curr_row = 0
            grid[(curr_col, curr_row)] = item
    return grid

def render_css_grid(grid, rows=6, cols=30, cell_size=24, road_type="big"):
    html = f'<div style="display: grid; grid-template-columns: repeat({cols}, {cell_size}px); grid-template-rows: repeat({rows}, {cell_size}px); gap: 0; background: #fff; border: 1px solid #ccc; width: max-content;">'
    for r in range(rows):
        for c in range(cols):
            cell = grid.get((c, r), None)
            content = ""
            if cell:
                val = cell['val'] if isinstance(cell, dict) else cell
                ties = cell.get('ties', 0) if isinstance(cell, dict) else 0
                
                if val in ['B', 'Red']: color = "#e81123"
                elif val in ['P', 'Blue']: color = "#0078d7"
                else: color = "#2ca02c"
                
                if road_type == "bead":
                    bg = "#e81123" if val == 'B' else "#0078d7" if val == 'P' else "#2ca02c"
                    txt = "莊" if val == 'B' else "閒" if val == 'P' else "和"
                    content = f'<div style="width:20px;height:20px;background:{bg};color:white;border-radius:50%;font-size:10px;line-height:20px;text-align:center;margin:auto;font-weight:bold;">{txt}</div>'
                elif road_type == "big":
                    content = f'<div style="position:relative;width:16px;height:16px;border:2px solid {color};border-radius:50%;margin:auto;">'
                    if ties > 0: content += f'<div style="position:absolute;width:20px;height:2px;background:#2ca02c;transform:rotate(-45deg);top:7px;left:-4px;"></div>'
                    content += '</div>'
                elif road_type == "big_eye": content = f'<div style="width:12px;height:12px;border:2px solid {color};border-radius:50%;margin:auto;"></div>'
                elif road_type == "small": content = f'<div style="width:12px;height:12px;background:{color};border-radius:50%;margin:auto;"></div>'
                elif road_type == "roach": content = f'<div style="width:16px;height:3px;background:{color};transform:rotate(-45deg);margin:auto;margin-top:8px;"></div>'
                
            html += f'<div style="border: 1px solid #eee; display: flex; align-items: center; justify-content: center;">{content}</div>'
    html += '</div>'
    return f'<div style="overflow-x: auto; padding-bottom: 10px;">{html}</div>'

big_road_list = []
for item in st.session_state.history:
    if item == 'T' and big_road_list: big_road_list[-1]['ties'] += 1
    elif item != 'T': big_road_list.append({'val': item, 'ties': 0})
        
logical_cols = build_logical_columns(st.session_state.history)

col_top1, col_top2 = st.columns([1, 2])
with col_top1:
    st.caption("珠盤路 (Bead Plate)")
    bead_grid = {(i // 6, i % 6): res for i, res in enumerate(st.session_state.history)}
    st.markdown(render_css_grid(bead_grid, cols=12, cell_size=28, road_type="bead"), unsafe_allow_html=True)
with col_top2:
    st.caption("大路 (Big Road)")
    st.markdown(render_css_grid(layout_road_matrix(big_road_list), cols=30, cell_size=28, road_type="big"), unsafe_allow_html=True)

st.caption("下三路 (Lower Three Roads)")
col_bot1, col_bot2, col_bot3 = st.columns(3)
with col_bot1: st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical_cols, 1)), cols=24, cell_size=18, road_type="big_eye"), unsafe_allow_html=True)
with col_bot2: st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical_cols, 2)), cols=24, cell_size=18, road_type="small"), unsafe_allow_html=True)
with col_bot3: st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical_cols, 3)), cols=24, cell_size=18, road_type="roach"), unsafe_allow_html=True)
