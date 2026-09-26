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

current_bet = 0; target = None; four_roads = {}; is_break = False; losses = 0; confidence = 50; recommend = '數據準備中...'; final_b=45.8; final_p=44.6; tie_ratio=9.5; status=''
if total_hands and run_monte_carlo_with_kelly:
    _, final_b, final_p, tie_ratio, recommend, four_roads, is_break, losses, status, resonance, confidence = run_monte_carlo_with_kelly(b_count,p_count,t_count,bankroll=st.session_state.bankroll,history_list=history,ai_targets=st.session_state.ai_targets,window=st.session_state.window,alpha=st.session_state.alpha)
    target = 'B' if '莊' in recommend else 'P' if '閒' in recommend else None
    if target:
        diff=abs(final_b-final_p)
        if st.session_state.strategy=='信號強弱 (1-2-3)': current_bet=st.session_state.base_unit*(3 if diff>=10 else 2 if diff>=5 else 1)
        elif st.session_state.strategy=='斐波那契 (Fibonacci)': current_bet=st.session_state.base_unit
        elif st.session_state.strategy=='雙頭龍': current_bet=st.session_state.base_unit
        else: current_bet=st.session_state.base_unit

m1,m2,m3,m4,m5=st.columns(5)
m1.metric('💰 當前資產',f'${st.session_state.bankroll:.2f}');m2.metric('💵 建議注碼',f'${current_bet}');m3.metric('📜 總局數',f'{total_hands}');m4.metric('莊/閒',f'{b_count} / {p_count}');m5.metric('和局率',f'{tie_ratio}%')
st.markdown('---')

if total_hands:
    level = '強訊號' if confidence >= 75 else '中訊號' if confidence >= 50 else '弱訊號'
    color = '#00ffcc' if level=='強訊號' else '#ffd166' if level=='中訊號' else '#aaa'
    st.markdown(f'''<div class="weight-box"><h2 style="margin:0;color:#00ffcc">🎯 {recommend}</h2><p><b>莊 {final_b}%</b> ｜ <b>閒 {final_p}%</b> ｜ <b style="color:{color}">訊號等級：{level}</b> ｜ 可信度 {confidence}%</p><small>{status}</small></div>''', unsafe_allow_html=True)
    if is_break: st.warning(f'⚔️ 反打機制生效：最近連敗 {losses} 局，請將訊號視為風險提示而非保證。')

if four_roads:
    st.markdown('#### 🔍 四大核心：訊號與特徵排排連')
    cols=st.columns(4)
    for col,(key,item) in zip(cols,four_roads.items()):
        ranking=item.get('feature_ranking',[])
        ranking_text=' ｜ '.join(f"{x['feature']} {x['value']:+.1f}" for x in ranking) or '沒有足夠特徵'
        with col:
            st.markdown(f'''<div class="pattern-card"><b>{item['name']}</b><br><span>{item['status']}</span><br><small>訊號：{item.get('signal_strength','弱訊號')}<br>特徵排名：{ranking_text}</small></div>''',unsafe_allow_html=True)

if total_hands and get_engine_diagnostics:
    with st.expander('📈 牌靴波動圖／動態門檻／詳細診斷', expanded=True):
        points=get_engine_diagnostics(history,st.session_state.ai_targets,st.session_state.window,st.session_state.alpha)
        chart=pd.DataFrame(points).set_index('局數')
        st.line_chart(chart[['weighted_score','big_road','big_eye','small_road','roach_road']])
        st.dataframe(chart.tail(10), use_container_width=True)
        st.caption('波動越大代表本靴各核心訊號分歧越大；動態門檻在樣本不足時會使用保守預設值。')

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
