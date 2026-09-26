import streamlit as st
import pandas as pd

try:
    from engine import run_monte_carlo_with_kelly, get_engine_diagnostics
except ImportError:
    run_monte_carlo_with_kelly = get_engine_diagnostics = None

st.set_page_config(page_title='Quantum Baccarat Dynamic OS', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<style>
#MainMenu,footer,header{visibility:hidden}.block-container{padding-top:.8rem!important;max-width:98%!important}
.stButton>button{height:48px;font-size:18px;font-weight:bold;border-radius:8px}.pattern-card{background:#1e2029;border:1px solid #333644;border-radius:8px;padding:12px;margin-bottom:8px}.weight-box{background:#0f1015;border:2px solid #00ffcc;padding:15px;border-radius:10px;text-align:center;margin-bottom:15px}.debug-box{background:#151720;border:1px solid #444;padding:10px;border-radius:8px}.stat-badge{font-weight:bold;padding:6px 16px;border-radius:6px;font-size:16px;color:white;display:inline-flex;gap:8px}.stat-b{background:#e81123}.stat-p{background:#0078d7}.stat-t{background:#2ca02c}.stat-tot{background:#8d6e63}
</style>''', unsafe_allow_html=True)

# session defaults
for key, default in [('history', []), ('ai_targets', []), ('bankroll', 10000), ('base_unit', 100), ('strategy', '信號強弱 (1-2-3)'), ('window', 50), ('alpha', .2)]:
    if key not in st.session_state:
        st.session_state[key] = default

history = st.session_state.history
b_count, p_count, t_count = history.count('B'), history.count('P'), history.count('T')
total_hands = len(history)

# ================= auto-adjust window & EMA (AI-driven) =================
import statistics

def auto_adjust_window_alpha(history):
    n = len([x for x in history if x in ('B','P')])
    if n < 30:
        window = 30
    elif n < 100:
        window = max(30, n // 2)
    else:
        window = 100
    # compute simple volatility on binary B/P series
    scores = [1 if x == 'B' else 0 for x in history if x in ('B','P')]
    if len(scores) >= 2:
        tail = scores[-window:] if len(scores) >= window else scores
        try:
            std = statistics.pstdev(tail)
        except Exception:
            std = 0.25
    else:
        std = 0.25
    # alpha scales with volatility (more volatile -> higher alpha to react faster)
    alpha = min(0.5, max(0.05, 0.1 + std * 1.5))
    return int(window), float(round(alpha, 3))

st.session_state.window, st.session_state.alpha = auto_adjust_window_alpha(history)

# ================= 預先計算歷史統計與資金策略 =================
fibo_idx = 0
double_dragon_idx = 0
tumbler_unit = 1

total_bets, wins, losses, pnl = 0, 0, 0, 0.0

for tgt, actual in zip(st.session_state.ai_targets, st.session_state.history):
    if tgt and tgt.get('target') and actual != 'T':
        total_bets += 1
        amt = tgt.get('amount', 0)
        if tgt['target'] == actual:
            wins += 1
            pnl += (amt * 0.95) if actual == 'B' else amt
            fibo_idx = max(0, fibo_idx - 2)
            double_dragon_idx = 0
            tumbler_unit = min(3, tumbler_unit + 1) if tumbler_unit < 3 else 1
        else:
            losses += 1
            pnl -= amt
            fibo_idx += 1
            double_dragon_idx += 1
            tumbler_unit = 1

current_bet = 0
target = None
recommend = "數據準備中..."
four_roads_data = {}
is_break_active = False
consec_losses = 0
markov_status = ""
is_resonance = False
confidence_pct = 50
final_b_pct, final_p_pct, actual_t_ratio = 45.8, 44.6, 9.5

# call engine with auto window/alpha
if total_hands > 0 and run_monte_carlo_with_kelly:
    # pass auto-adjusted window/alpha to engine
    try:
        result = run_monte_carlo_with_kelly(
            b_count, p_count, t_count,
            bankroll=st.session_state.bankroll,
            sim_count=0,
            history_list=history,
            ai_targets=st.session_state.ai_targets,
            window=st.session_state.window,
            alpha=st.session_state.alpha,
        )
    except TypeError:
        # fallback if engine doesn't accept window/alpha
        result = run_monte_carlo_with_kelly(
            b_count, p_count, t_count,
            bankroll=st.session_state.bankroll,
            sim_count=0,
            history_list=history,
            ai_targets=st.session_state.ai_targets,
        )
    if result:
        if isinstance(result, (list, tuple)) and len(result) >= 10:
            # support both short and extended tuples
            try:
                _, final_b_pct, final_p_pct, actual_t_ratio, recommend, four_roads_data, is_break_active, consec_losses, markov_status, is_resonance, confidence_pct = result[:11]
            except Exception:
                # try unpacking more fields if present
                try:
                    _, final_b_pct, final_p_pct, actual_t_ratio, recommend, four_roads_data, is_break_active, consec_losses, markov_status, is_resonance, confidence_pct, *rest = result
                except Exception:
                    pass

    target = 'B' if '莊' in recommend else 'P' if '閒' in recommend else None
    if target:
        diff = abs(final_b_pct - final_p_pct)
        if st.session_state.strategy == '信號強弱 (1-2-3)':
            # use simple multiplier mapping
            if confidence_pct >= 80:
                mult = 2.0
            elif confidence_pct >= 60:
                mult = 1.2
            else:
                mult = 1.0
            if four_roads_data:
                strong_count = sum(1 for r in four_roads_data.values() if r.get('signal_strength') == '強訊號')
                mult += 0.2 * max(0, strong_count - 1)
            current_bet = max(1, int(round(st.session_state.base_unit * mult)))
        elif st.session_state.strategy == '斐波那契 (Fibonacci)':
            fibo_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
            idx = min(fibo_idx, len(fibo_seq) - 1)
            current_bet = st.session_state.base_unit * fibo_seq[idx]
        elif st.session_state.strategy == '雙頭龍':
            dd_seq = [1, 1, 2, 2, 4, 4, 8, 8, 16, 16, 32, 32]
            idx = min(double_dragon_idx, len(dd_seq) - 1)
            current_bet = st.session_state.base_unit * dd_seq[idx]
        else:
            current_bet = st.session_state.base_unit

# ================= 2. 資金管理與注碼策略 + 快速輸入 (並列布局) =================
st.markdown('### ⚙️ 資金管理與注碼策略 (實時整合監控)')
left, right = st.columns([2, 1.1])

with left:
    c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
    st.session_state.bankroll = c1.number_input('💰 初始總本金 ($)', min_value=100, value=st.session_state.bankroll, step=500)
    st.session_state.base_unit = c2.number_input('💵 基礎注碼 ($)', min_value=10, value=st.session_state.base_unit, step=10)
    st.session_state.strategy = c3.selectbox('📈 注碼策略', ['信號強弱 (1-2-3)','斐波那契 (Fibonacci)','雙頭龍','不倒翁投注法'])

    # summary / diagnostics
    st.markdown('')
    st.write(f'當前總本金：${st.session_state.bankroll:.2f}  ｜ 建議注碼：${current_bet}')
    st.write(f'總局數：{total_hands} ｜ 莊/閒：{b_count}/{p_count} ｜ 和局：{t_count}')
    st.write(f'動態窗口(window) = {st.session_state.window} ，EMA α = {st.session_state.alpha}')

with right:
    st.markdown('##### 🎛️ 快速開牌輸入')
    btn_cols = st.columns(4)
    def record_hand(result):
        st.session_state.ai_targets.append({'target': target, 'amount': current_bet} if target else None)
        st.session_state.history.append(result)
        st.rerun()

    if btn_cols[0].button('🔴 開莊 (B)', use_container_width=True): record_hand('B')
    if btn_cols[1].button('🔵 開閒 (P)', use_container_width=True): record_hand('P')
    if btn_cols[2].button('🟢 開和 (T)', use_container_width=True): record_hand('T')
    if btn_cols[3].button('↩️ 撤銷', use_container_width=True):
        if st.session_state.history:
            st.session_state.history.pop()
            st.session_state.ai_targets.pop()
        st.rerun()

    with st.expander('📝 批量輸入歷史賽果', expanded=False):
        batch_input = st.text_input('請輸入歷史賽果 (例如: BBPTP...)')
        if st.button('📥 載入歷史', use_container_width=True):
            cleaned = []
            for char in batch_input:
                if char.upper() in ('B','P','T'): cleaned.append(char.upper())
                elif char in ('莊','庄'): cleaned.append('B')
                elif char in ('閒','闲'): cleaned.append('P')
                elif char == '和': cleaned.append('T')
            if cleaned:
                st.session_state.history.extend(cleaned)
                st.session_state.ai_targets.extend([None] * len(cleaned))
                st.rerun()

# metrics row
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric('💰 當前資產', f'${st.session_state.bankroll + pnl:.2f}')
m2.metric('💵 建議注碼', f'${current_bet}')
m3.metric('📜 總局數', f'{total_hands}')
m4.metric('莊/閒', f'{b_count} / {p_count}')
m5.metric('和局率', f'{actual_t_ratio}%')

st.markdown('---')

# ================= 3. AI 預測建議與四路顯示 =================
st.markdown('### 🧠 最終權重預測建議 (雙重 AI 自主學習引擎)')
if total_hands:
    resonance_tag = ' 🔥【三路共振爆發點】' if is_resonance else ''
    st.markdown(f"""
    <div class="weight-box">
        <h2 style="margin:0; color:#00ffcc;">🎯 最終權重建議：{recommend}{resonance_tag}</h2>
        <p style="font-size: 18px; margin-top:8px;">
            <b>莊家歸一化權重：<span style="color:#ff4b4b;">{final_b_pct}%</span></b> ｜ 
            <b>閒家歸一化權重：<span style="color:#1f77b4;">{final_p_pct}%</span></b> ｜ 
            <b>訊號可信度指數：<span style="color:#00ffcc;">{confidence_pct}%</span></b>
        </p>
        <small style="color:#aaa;">[{markov_status}]</small>
    </div>
    """, unsafe_allow_html=True)

if four_roads_data:
    st.markdown('#### 🔍 4 大核心路單獨立診斷 (動態 AI 配比 + 獨立馬爾可夫)')
    r_cols = st.columns(4)
    r_keys = list(four_roads_data.keys())
    for i, k in enumerate(r_keys):
        item = four_roads_data[k]
        color = 'red' if item.get('dominant') == 'B' else ('blue' if item.get('dominant') == 'P' else 'gray')
        with r_cols[i]:
            st.markdown(f"""
            <div class="pattern-card">
                <b>{item.get('name')}</b><br>
                <span style="color:{color}; font-size:13px; font-weight:bold;">{item.get('status')}</span><br>
                <small style="color:#aaa;">特徵與馬爾可夫: {', '.join(item.get('details') or []) if item.get('details') else '無明顯特徵'}</small>
            </div>
            """, unsafe_allow_html=True)

# --- Five-road helpers & rendering (kept unchanged) ---
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

def render_css_grid(grid, rows=6, cols=30, cell_size=24, road_type='big'):
    html = '<div style="display: grid; grid-template-columns: repeat({}, {}px); grid-template-rows: repeat({}, {}px); gap: 0; background: #fff; border: 1px solid #ccc; width: max-content;">'.format(cols, cell_size, rows, cell_size)
    for r in range(rows):
        for c in range(cols):
            cell = grid.get((c, r), None)
            content = ''
            if cell:
                val = cell['val'] if isinstance(cell, dict) else cell
                ties = cell.get('ties', 0) if isinstance(cell, dict) else 0
                if val in ['B', 'Red']:
                    color = '#e81123'
                elif val in ['P', 'Blue']:
                    color = '#0078d7'
                else:
                    color = '#2ca02c'
                if road_type == 'bead':
                    bg = '#e81123' if val == 'B' else '#0078d7' if val == 'P' else '#2ca02c'
                    txt = '莊' if val == 'B' else '閒' if val == 'P' else '和'
                    content = '<div style="width:20px;height:20px;background:{};color:white;border-radius:50%;font-size:10px;line-height:20px;text-align:center;margin:auto;font-weight:bold;">{}</div>'.format(bg, txt)
                elif road_type == 'big':
                    content = '<div style="position:relative;width:16px;height:16px;border:2px solid {};border-radius:50%;margin:auto;">'.format(color)
                    if ties > 0:
                        content += '<div style="position:absolute;width:20px;height:2px;background:#2ca02c;transform:rotate(-45deg);top:7px;left:-4px;"></div>'
                    content += '</div>'
                elif road_type == 'big_eye':
                    content = '<div style="width:12px;height:12px;border:2px solid {};border-radius:50%;margin:auto;"></div>'.format(color)
                elif road_type == 'small':
                    content = '<div style="width:12px;height:12px;background:{};border-radius:50%;margin:auto;"></div>'.format(color)
                elif road_type == 'roach':
                    content = '<div style="width:16px;height:3px;background:{};transform:rotate(-45deg);margin:auto;margin-top:8px;"></div>'.format(color)
            html += '<div style="border: 1px solid #eee; display: flex; align-items: center; justify-content: center;">{}</div>'.format(content)
    html += '</div>'
    return '<div style="overflow-x: auto; padding-bottom: 10px;">{}</div>'.format(html)

def get_ask_road_symbols(history, test_val):
    temp_hist = history + [test_val]
    temp_cols = build_logical_columns(temp_hist)
    e = get_derived_road(temp_cols, 1)
    s = get_derived_road(temp_cols, 2)
    r = get_derived_road(temp_cols, 3)
    return (e[-1] if e else None, s[-1] if s else None, r[-1] if r else None)

def draw_ask_icon(val, r_type):
    if not val: return "<div style='width:18px; height:18px;'></div>"
    color = "#e81123" if val == 'Red' else "#0078d7"
    if r_type == 'eye': return f"<div style='width:14px;height:14px;border:2px solid {color};border-radius:50%;'></div>"
    if r_type == 'small': return f"<div style='width:14px;height:14px;background:{color};border-radius:50%;'></div>"
    if r_type == 'roach': return f"<div style='width:14px;height:3px;background:{color};transform:rotate(-45deg);margin-top:5px;'></div>"

# --- 4B. 專業娛樂城路紙 (五路全開) ---
big_road_list = []
for item in st.session_state.history:
    if item == 'T' and big_road_list: big_road_list[-1]['ties'] += 1
    elif item != 'T': big_road_list.append({'val': item, 'ties': 0})

logical_cols = build_logical_columns(st.session_state.history)

col_top1, col_top2 = st.columns([1, 2])
with col_top1:
    st.caption('珠盤路 (Bead Plate)')
    bead_grid = {(i // 6, i % 6): res for i, res in enumerate(st.session_state.history)}
    st.markdown(render_css_grid(bead_grid, cols=12, cell_size=28, road_type='bead'), unsafe_allow_html=True)
with col_top2:
    st.caption('大路 (Big Road)')
    st.markdown(render_css_grid(layout_road_matrix(big_road_list), cols=30, cell_size=28, road_type='big'), unsafe_allow_html=True)

st.caption('下三路 (Lower Three Roads)')
col_bot1, col_bot2, col_bot3 = st.columns(3)
with col_bot1:
    st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical_cols, 1)), cols=24, cell_size=18, road_type='big_eye'), unsafe_allow_html=True)
with col_bot2:
    st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical_cols, 2)), cols=24, cell_size=18, road_type='small'), unsafe_allow_html=True)
with col_bot3:
    st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical_cols, 3)), cols=24, cell_size=18, road_type='roach'), unsafe_allow_html=True)

# bottom stats and ask road cards
ask_b = get_ask_road_symbols(st.session_state.history, 'B')
ask_p = get_ask_road_symbols(st.session_state.history, 'P')

st.markdown('<br>', unsafe_allow_html=True)
col_stat_left, col_ask_right = st.columns([1, 1])
with col_stat_left:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 5px;">
        <div class="stat-badge stat-b">莊 <span style="font-size:22px;">{b_count}</span></div>
        <div class="stat-badge stat-p">閒 <span style="font-size:22px;">{p_count}</span></div>
        <div class="stat-badge stat-t">和 <span style="font-size:22px;">{t_count}</span></div>
        <div class="stat-badge stat-tot">總 <span style="font-size:22px;">{total_hands}</span></div>
    </div>
    """, unsafe_allow_html=True)
with col_ask_right:
    st.markdown(f"""
    <div style="display: flex; gap: 12px; justify-content: flex-end; align-items: center; margin-top: 5px;">
        <div class="ask-btn-box ask-btn-b">
            <span>莊問路</span>
            <div class="ask-icon-group">
                {draw_ask_icon(ask_b[0], 'eye')}
                {draw_ask_icon(ask_b[1], 'small')}
                {draw_ask_icon(ask_b[2], 'roach')}
            </div>
        </div>
        <div class="ask-btn-box ask-btn-p">
            <span>閒問路</span>
            <div class="ask-icon-group">
                {draw_ask_icon(ask_p[0], 'eye')}
                {draw_ask_icon(ask_p[1], 'small')}
                {draw_ask_icon(ask_p[2], 'roach')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# diagnostics and chart
if total_hands and get_engine_diagnostics:
    with st.expander('📈 牌靴波動圖／動態門檻／詳細診斷', expanded=True):
        points=get_engine_diagnostics(history,st.session_state.ai_targets,st.session_state.window,st.session_state.alpha)
        chart=pd.DataFrame(points).set_index('局數')
        st.line_chart(chart[['weighted_score','big_road','big_eye','small_road','roach_road']])
        st.dataframe(chart.tail(10), use_container_width=True)
        st.caption('波動越大代表本靴各核心訊號分歧越大；動態門檻在樣本不足時會使用保守預設值。')

st.markdown('---')
