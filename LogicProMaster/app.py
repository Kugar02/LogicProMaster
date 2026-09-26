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

for key, default in [('history', []), ('ai_targets', []), ('bankroll', 10000), ('base_unit', 100), ('strategy', '信號強弱 (1-2-3)'), ('window', 50), ('alpha', .2)]:
    if key not in st.session_state: st.session_state[key] = default

history = st.session_state.history
b_count, p_count, t_count = history.count('B'), history.count('P'), history.count('T')
total_hands = len(history)

st.markdown('### ⚙️ 資金管理與動態牌靴參數')
c1,c2,c3,c4,c5 = st.columns([1.2,1.2,1.7,1.1,1.1])
st.session_state.bankroll = c1.number_input('💰 本金', min_value=100, value=st.session_state.bankroll, step=500)
st.session_state.base_unit = c2.number_input('💵 基礎注碼', min_value=10, value=st.session_state.base_unit, step=10)
st.session_state.strategy = c3.selectbox('📈 注碼策略', ['信號強弱 (1-2-3)','斐波那契 (Fibonacci)','雙頭龍','不倒翁投注法'])
st.session_state.window = c4.number_input('📊 動態窗口', 8, 200, st.session_state.window, 2)
st.session_state.alpha = c5.number_input('EMA α', .05, .95, st.session_state.alpha, .05)
if st.button('🗑️ 清空重置 (新靴)', use_container_width=True):
    st.session_state.history=[]; st.session_state.ai_targets=[]; st.rerun()

# ------------------ Reintroduce road rendering helpers ------------------

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


def render_css_grid(grid, rows=6, cols=30, cell_size=24, road_type="big"):
    # Use .format() to avoid f-string braces conflicts in HTML/CSS
    html = '<div style="display: grid; grid-template-columns: repeat({}, {}px); grid-template-rows: repeat({}, {}px); gap: 0; background: #fff; border: 1px solid #ccc; width: max-content;">'.format(cols, cell_size, rows, cell_size)
    for r in range(rows):
        for c in range(cols):
            cell = grid.get((c, r), None)
            content = ""
            if cell:
                val = cell['val'] if isinstance(cell, dict) else cell
                ties = cell.get('ties', 0) if isinstance(cell, dict) else 0
                if val in ['B', 'Red']:
                    color = "#e81123"
                elif val in ['P', 'Blue']:
                    color = "#0078d7"
                else:
                    color = "#2ca02c"
                if road_type == "bead":
                    bg = "#e81123" if val == 'B' else "#0078d7" if val == 'P' else "#2ca02c"
                    txt = "莊" if val == 'B' else "閒" if val == 'P' else "和"
                    content = '<div style="width:20px;height:20px;background:{};color:white;border-radius:50%;font-size:10px;line-height:20px;text-align:center;margin:auto;font-weight:bold;">{}</div>'.format(bg, txt)
                elif road_type == "big":
                    content = '<div style="position:relative;width:16px;height:16px;border:2px solid {};border-radius:50%;margin:auto;">'.format(color)
                    if ties > 0:
                        content += '<div style="position:absolute;width:20px;height:2px;background:#2ca02c;transform:rotate(-45deg);top:7px;left:-4px;"></div>'
                    content += '</div>'
                elif road_type == "big_eye":
                    content = '<div style="width:12px;height:12px;border:2px solid {};border-radius:50%;margin:auto;"></div>'.format(color)
                elif road_type == "small":
                    content = '<div style="width:12px;height:12px;background:{};border-radius:50%;margin:auto;"></div>'.format(color)
                elif road_type == "roach":
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

# ---------------------------------------------------------------------------

current_bet = 0; target = None; four_roads = {}; is_break = False; losses = 0; confidence = 50; recommend = '數據準備中...'; final_b=45.8; final_p=44.6; tie_ratio=9.5; status=''
if total_hands and run_monte_carlo_with_kelly:
    result = run_monte_carlo_with_kelly(b_count,p_count,t_count,bankroll=st.session_state.bankroll,history_list=history,ai_targets=st.session_state.ai_targets,window=st.session_state.window,alpha=st.session_state.alpha)
    if result:
        if len(result) >= 13:
            _, final_b, final_p, tie_ratio, recommend, four_roads, is_break, losses, status, resonance, confidence, level, thresholds = result
        else:
            _, final_b, final_p, tie_ratio, recommend, four_roads, is_break, losses, status, resonance, confidence = result

    target = 'B' if '莊' in recommend else 'P' if '閒' in recommend else None
    if target:
        diff=abs(final_b-final_p)
        if st.session_state.strategy=='信號強弱 (1-2-3)':
            if 'level' in locals():
                map_vals = {'強訊號':2.0,'中訊號':1.0,'弱訊號':0.5}
                mult = map_vals.get(level,1.0)
                extra=0.0
                if four_roads:
                    strong_count=sum(1 for r in four_roads.values() if r.get('signal_strength')=='強訊號')
                    mid_count=sum(1 for r in four_roads.values() if r.get('signal_strength')=='中訊號')
                    extra += 0.2 * max(0, strong_count - 1)
                    extra += 0.05 * mid_count
                current_bet = int(max(1, round(st.session_state.base_unit * (mult + extra))))
            else:
                current_bet=st.session_state.base_unit*(3 if diff>=10 else 2 if diff>=5 else 1)
        elif st.session_state.strategy=='斐波那契 (Fibonacci)':
            fibo_seq=[1,1,2,3,5,8,13,21,34,55,89,144]
            idx=0
            current_bet=st.session_state.base_unit*fibo_seq[idx]
        elif st.session_state.strategy=='雙頭龍':
            current_bet=st.session_state.base_unit
        else:
            current_bet=st.session_state.base_unit

m1,m2,m3,m4,m5=st.columns(5)
m1.metric('💰 當前資產',f'${st.session_state.bankroll:.2f}');m2.metric('💵 建議注碼',f'${current_bet}');m3.metric('📜 總局���',f'{total_hands}');m4.metric('莊/閒',f'{b_count} / {p_count}');m5.metric('和局率',f'{tie_ratio}%')
st.markdown('---')

# display weight box
if total_hands:
    level = '強訊號' if confidence >= 75 else '中訊號' if confidence >= 50 else '弱訊號'
    color = '#00ffcc' if level=='強訊號' else '#ffd166' if level=='中訊號' else '#aaa'
    st.markdown(f'''<div class="weight-box"><h2 style="margin:0;color:#00ffcc">🎯 {recommend}</h2><p><b>莊 {final_b}%</b> ｜ <b>閒 {final_p}%</b> ｜ <b style="color:{color}">訊號等級：{level}</b> ｜ 可信度 {confidence}%</p><small>{status}</small></div>''', unsafe_allow_html=True)
    if is_break: st.warning(f'⚔️ 反打機制生效：最近連敗 {losses} 局，請將訊號視為風險提示而非保證。')

# Four roads display + five-road rendering
if four_roads:
    st.markdown('#### 🔍 四大核心：訊號與特徵排排連')
    cols=st.columns(4)
    for col,(key,item) in zip(cols,four_roads.items()):
        ranking=item.get('feature_ranking',[])
        ranking_text=' ｜ '.join(f"{x['feature']} {x['value']:+.1f}" for x in ranking) or '沒有足夠特徵'
        with col:
            st.markdown(f'''<div class="pattern-card"><b>{item['name']}</b><br><span>{item['status']}</span><br><small>訊號：{item.get('signal_strength','弱訊號')}<br>特徵排名：{ranking_text}</small></div>''',unsafe_allow_html=True)

# --- Classic five-road UI ---

st.markdown('##### 📊 專業娛樂城路紙 (五路全開)')

big_road_list = []
for item in history:
    if item == 'T' and big_road_list: big_road_list[-1]['ties'] += 1
    elif item != 'T': big_road_list.append({'val': item, 'ties': 0})

logical_cols = build_logical_columns(history)

col_top1, col_top2 = st.columns([1, 2])
with col_top1:
    st.caption('珠盤路 (Bead Plate)')
    bead_grid = {(i // 6, i % 6): res for i, res in enumerate(history)}
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
ask_b = get_ask_road_symbols(history, 'B')
ask_p = get_ask_road_symbols(history, 'P')

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

# record / input UI
st.markdown('---'); st.markdown('### 🎛️ 開牌紀錄與快捷輸入')
def record(result):
    st.session_state.ai_targets.append({'target':target,'amount':current_bet} if target else None); st.session_state.history.append(result); st.rerun()
b1,b2,b3,b4=st.columns(4)
if b1.button('🔴 開莊 (B)',use_container_width=True): record('B')
if b2.button('🔵 開閒 (P)',use_container_width=True): record('P')
if b3.button('🟢 開和 (T)',use_container_width=True): record('T')
if b4.button('↩️ 撤銷上一手',use_container_width=True):
    if st.session_state.history: st.session_state.history.pop(); st.session_state.ai_targets.pop()
    st.rerun()
with st.expander('📝 批量輸入歷史賽果'):
    batch=st.text_input('例如 BBPTP...')
    if st.button('📥 載入'):
        cleaned=[]
        for char in batch:
            if char.upper() in ('B','P','T'): cleaned.append(char.upper())
            elif char in ('莊','庄'): cleaned.append('B')
            elif char in ('閒','闲'): cleaned.append('P')
            elif char=='和': cleaned.append('T')
        if cleaned: st.session_state.history.extend(cleaned);st.session_state.ai_targets.extend([None]*len(cleaned));st.rerun()

st.markdown('---')
st.markdown(f'''<div><span class="stat-badge stat-b">莊 {b_count}</span> <span class="stat-badge stat-p">閒 {p_count}</span> <span class="stat-badge stat-t">和 {t_count}</span> <span class="stat-badge stat-tot">總 {total_hands}</span></div>''',unsafe_allow_html=True)
