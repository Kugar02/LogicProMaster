import streamlit as st
import pandas as pd

# 嘗試載入計算引擎 (若有 engine.py 則啟動，無則純顯示路單)
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
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state: st.session_state.history = []
if 'bankroll' not in st.session_state: st.session_state.bankroll = 10000

# ================= 2. 下三路核心演算法 =================

def build_logical_columns(history):
    """將歷史轉換為純莊閒的邏輯列（忽略和局），用於下三路比對"""
    cols = []
    current_col = []
    last_res = None
    for res in history:
        if res == 'T': continue
        if res != last_res:
            if current_col: cols.append(current_col)
            current_col = [res]
            last_res = res
        else:
            current_col.append(res)
    if current_col: cols.append(current_col)
    return cols

def get_derived_road(cols, k):
    """
    計算下三路 (k=1: 大眼仔, k=2: 小路, k=3: 曱甴路)
    回傳 'R' (紅) 或 'B' (藍) 的一維陣列
    """
    derived = []
    for c in range(1, len(cols)):
        for r in range(len(cols[c])):
            if c < k: continue # 該路還沒開始
            
            if r == 0:
                if c < k + 1: continue
                # 換列時 (第一格)：比對前一列與參考列的長度
                len_prev = len(cols[c-1])
                len_ref = len(cols[c-1-k])
                derived.append('R' if len_prev == len_ref else 'B')
            else:
                # 直落時 (第二格起)：比對參考列是否有該格
                len_ref = len(cols[c-k])
                if len_ref >= r + 1: # 參考列有此格 (拍腳)
                    derived.append('R')
                elif len_ref == r: # 參考列剛好缺此格
                    derived.append('B')
                else: # 參考列缺很多格 (長莊/長閒)
                    derived.append('R')
    return derived

def layout_road_matrix(data_list, rows=6):
    """通用的路單排版引擎 (支援長龍向右拐彎)"""
    grid = {}
    curr_col, curr_row = 0, 0
    start_col = 0
    last_val = None
    
    for item in data_list:
        if last_val is None:
            last_val = item
            grid[(curr_col, curr_row)] = item
        elif item == last_val:
            curr_row += 1
            # 碰底或撞牆，向右拐彎
            if curr_row >= rows or (curr_col, curr_row) in grid:
                curr_row -= 1
                curr_col += 1
            grid[(curr_col, curr_row)] = item
        else:
            last_val = item
            start_col += 1
            curr_col = start_col
            # 尋找第一列空位開新局
            while (curr_col, 0) in grid:
                curr_col += 1
            start_col = curr_col
            curr_row = 0
            grid[(curr_col, curr_row)] = item
    return grid

# ================= 3. HTML 渲染引擎 =================

def render_grid_html(grid, rows=6, cols=20, cell_size=20, road_type="big"):
    html = f'<table style="border-collapse: collapse; background: #fff; table-layout: fixed; margin: auto;">'
    for r in range(rows):
        html += '<tr>'
        for c in range(cols):
            cell = grid.get((c, r), None)
            content = ""
            if cell:
                # 解析資料 (大路可能包含和局字典，下三路只有純字串)
                val = cell['val'] if isinstance(cell, dict) else cell
                ties = cell.get('ties', 0) if isinstance(cell, dict) else 0
                
                # 顏色定義
                color = "#e81123" if val in ['B', 'R'] else "#0078d7"
                
                # 依照路單類型畫不同的符號
                if road_type == "bead":
                    bg = "#e81123" if val == 'B' else "#0078d7" if val == 'P' else "#2ca02c"
                    txt = "莊" if val == 'B' else "閒" if val == 'P' else "和"
                    content = f'<div style="width:20px;height:20px;background:{bg};color:white;border-radius:50%;font-size:10px;line-height:20px;text-align:center;margin:auto;font-weight:bold;">{txt}</div>'
                elif road_type == "big":
                    content = f'<div style="position:relative;width:14px;height:14px;border:2px solid {color};border-radius:50%;margin:auto;">'
                    if ties > 0:
                        content += f'<div style="position:absolute;width:18px;height:2px;background:#2ca02c;transform:rotate(-45deg);top:6px;left:-4px;"></div>'
                    content += '</div>'
                elif road_type == "big_eye":
                    # 大眼仔：小空心圓
                    content = f'<div style="width:10px;height:10px;border:2px solid {color};border-radius:50%;margin:auto;"></div>'
                elif road_type == "small":
                    # 小路：實心圓
                    content = f'<div style="width:10px;height:10px;background:{color};border-radius:50%;margin:auto;"></div>'
                elif road_type == "roach":
                    # 曱甴路：斜線
                    content = f'<div style="width:12px;height:2px;background:{color};transform:rotate(-45deg);margin:auto;margin-top:8px;"></div>'
                    
            html += f'<td style="border: 1px solid #eee; width: {cell_size}px; height: {cell_size}px; text-align: center; vertical-align: middle;">{content}</td>'
        html += '</tr>'
    html += '</table>'
    return html

# ================= 4. UI 介面配置 =================
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
if c1.button("🔴 開莊 (B)", use_container_width=True): st.session_state.history.append('B')
if c2.button("🔵 開閒 (P)", use_container_width=True): st.session_state.history.append('P')
if c3.button("🟢 開和 (T)", use_container_width=True): st.session_state.history.append('T')
if c4.button("↩️ 撤銷上一手", use_container_width=True): 
    if st.session_state.history: st.session_state.history.pop()

# --- 處理大路數據 (獨立處理和局) ---
big_road_list = []
for item in st.session_state.history:
    if item == 'T' and big_road_list:
        big_road_list[-1]['ties'] += 1
    elif item != 'T':
        big_road_list.append({'val': item, 'ties': 0})
        
# --- 產生路單矩陣 ---
big_road_grid = layout_road_matrix(big_road_list)
logical_cols = build_logical_columns(st.session_state.history)

big_eye_list = get_derived_road(logical_cols, 1)
small_road_list = get_derived_road(logical_cols, 2)
roach_road_list = get_derived_road(logical_cols, 3)

# ================= 5. 渲染五大路單 =================
st.markdown("### 📊 專業娛樂城路紙 (五路全開)")

col_top1, col_top2 = st.columns([2, 5])
with col_top1:
    st.caption("珠盤路 (Bead Plate)")
    bead_grid = {(i // 6, i % 6): res for i, res in enumerate(st.session_state.history)}
    st.markdown(f'<div class="road-container">{render_grid_html(bead_grid, cols=12, cell_size=26, road_type="bead")}</div>', unsafe_allow_html=True)

with col_top2:
    st.caption("大路 (Big Road)")
    st.markdown(f'<div class="road-container">{render_grid_html(big_road_grid, cols=42, cell_size=26, road_type="big")}</div>', unsafe_allow_html=True)

st.caption("下三路 (Lower Three Roads: 大眼仔路 / 小路 / 曱甴路)")
col_bot1, col_bot2, col_bot3 = st.columns(3)

with col_bot1:
    grid = layout_road_matrix(big_eye_list)
    st.markdown(f'<div class="road-container">{render_grid_html(grid, cols=28, cell_size=18, road_type="big_eye")}</div>', unsafe_allow_html=True)

with col_bot2:
    grid = layout_road_matrix(small_road_list)
    st.markdown(f'<div class="road-container">{render_grid_html(grid, cols=28, cell_size=18, road_type="small")}</div>', unsafe_allow_html=True)

with col_bot3:
    grid = layout_road_matrix(roach_road_list)
    st.markdown(f'<div class="road-container">{render_grid_html(grid, cols=28, cell_size=18, road_type="roach")}</div>', unsafe_allow_html=True)


# ================= 6. 莊閒精確問路 (Ask Road) =================
def get_ask_road_symbols(history, test_val):
    """預測下一手開莊/閒時，下三路會出的顏色"""
    temp_hist = history + [test_val]
    temp_cols = build_logical_columns(temp_hist)
    e = get_derived_road(temp_cols, 1)
    s = get_derived_road(temp_cols, 2)
    r = get_derived_road(temp_cols, 3)
    return (
        e[-1] if e else None, 
        s[-1] if s else None, 
        r[-1] if r else None
    )

ask_b = get_ask_road_symbols(st.session_state.history, 'B')
ask_p = get_ask_road_symbols(st.session_state.history, 'P')

def draw_ask_icon(val, r_type):
    if not val: return "<div style='width:20px; height:20px;'></div>"
    color = "#e81123" if val == 'R' else "#0078d7"
    if r_type == 'eye': return f"<div style='width:16px;height:16px;border:3px solid {color};border-radius:50%;'></div>"
    if r_type == 'small': return f"<div style='width:16px;height:16px;background:{color};border-radius:50%;'></div>"
    if r_type == 'roach': return f"<div style='width:16px;height:4px;background:{color};transform:rotate(-45deg);margin-top:6px;'></div>"

st.markdown("### 🔮 莊閒問路")
col_ask_b, col_ask_p = st.columns(2)

with col_ask_b:
    st.markdown(f"""
    <div class="ask-road-box">
        <h4 style="color:#e81123; margin:0;">🔴 莊問路 (Banker)</h4>
        <div class="ask-icons">
            {draw_ask_icon(ask_b[0], 'eye')} {draw_ask_icon(ask_b[1], 'small')} {draw_ask_icon(ask_b[2], 'roach')}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_ask_p:
    st.markdown(f"""
    <div class="ask-road-box">
        <h4 style="color:#0078d7; margin:0;">🔵 閒問路 (Player)</h4>
        <div class="ask-icons">
            {draw_ask_icon(ask_p[0], 'eye')} {draw_ask_icon(ask_p[1], 'small')} {draw_ask_icon(ask_p[2], 'roach')}
        </div>
    </div>
    """, unsafe_allow_html=True)
