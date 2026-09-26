import streamlit as st
import pandas as pd
import time
from engine import run_monte_carlo_with_kelly
try:
    from scraper import MTLiveScraper
except ImportError:
    MTLiveScraper = None

# 1. 網頁頂層配置：強製寬螢幕、暗色調專業數據終端風格
st.set_page_config(
    page_title="MT-Live 百家樂凱利量化終端 Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 自訂 CSS 樣式美化介面
st.markdown("""
<style>
    .reportview-container { background: #121212; }
    .main-title { font-size: 32px !important; font-weight: 700 !important; color: #F0A500 !important; text-align: left; margin-bottom: 5px; }
    .sub-title { font-size: 14px !important; color: #888888 !important; margin-bottom: 25px; }
    .stButton>button { border-radius: 8px !important; font-weight: 600 !important; }
    .metric-card { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🃏 MT Live 百家樂大數據分析與凱利注碼盈利模擬終端</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">版本 3.5 | 標準百家樂 5% 抽水設定 | 1/4 凱利安全資金控制 | 雲端高密計算 Web UI 版本</p>', unsafe_allow_html=True)

# 初始化核心數據 Session State
if 'b_count' not in st.session_state: st.session_state.b_count = 0
if 'p_count' not in st.session_state: st.session_state.p_count = 0
if 't_count' not in st.session_state: st.session_state.t_count = 0
if 'scraper_instance' not in st.session_state: st.session_state.scraper_instance = None
if 'auto_sync' not in st.session_state: st.session_state.auto_sync = False

# ==================== SIDEBAR: 資金與全局環境設定 ====================
st.sidebar.markdown("### 💰 全局資金管理設定")
total_bankroll = st.sidebar.number_input("當前賬戶總本金 (\$)", min_value=100, value=10000, step=500)
sim_runs = st.sidebar.slider("蒙地卡羅模擬次數 (次)", min_value=5000, max_value=50000, value=20000, step=5000)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔌 自動盯盤抓取設定")
casino_url = st.sidebar.text_input("娛樂城登入網址", value="https://example-casino.com")

col_auto1, col_auto2 = st.sidebar.columns(2)
with col_auto1:
    if st.sidebar.button("🔗 啟動瀏覽器", use_container_width=True):
        if MTLiveScraper:
            st.session_state.scraper_instance = MTLiveScraper(casino_url)
            st.session_state.scraper_instance.start_monitoring()
            st.sidebar.success("✅ 瀏覽器就緒")
        else:
            st.sidebar.error("找不到 scraper.py 模組")
with col_auto2:
    st.session_state.auto_sync = st.sidebar.checkbox("🔄 開啟同步", value=st.session_state.auto_sync)

# 執行自動同步數據邏輯
trigger_calc = False
if st.session_state.auto_sync and st.session_state.scraper_instance:
    scores = st.session_state.scraper_instance.get_live_scores()
    if scores:
        st.session_state.b_count, st.session_state.p_count, st.session_state.t_count = scores
        st.toast(f"⚡ 數據已同步：{scores[0]}莊 {scores[1]}閒 {scores[2]}和")
        trigger_calc = True
    time.sleep(1) # 溫和刷新頻率

# ==================== MAIN LAYOUT: 左右雙欄佈局 ====================
left_column, right_column = st.columns([1, 2]) # 1:2 比例黃金分割

# -------------------- 左側欄：控制面板與手動微調 --------------------
with left_column:
    st.markdown("### 🎛️ 實時開牌手動輸入")
    
    col_b, col_p, col_t = st.columns(3)
    with col_b:
        if st.button("🔴 莊 (Banker)", use_container_width=True, type="secondary"):
            st.session_state.b_count += 1
            trigger_calc = True
    with col_p:
        if st.button("🔵 閒 (Player)", use_container_width=True, type="secondary"):
            st.session_state.p_count += 1
            trigger_calc = True
    with col_t:
        if st.button("🟢 和 (Tie)", use_container_width=True, type="secondary"):
            st.session_state.t_count += 1
            trigger_calc = True
            
    st.markdown("#### 📋 歷史總量精確校正")
    st.session_state.b_count = st.number_input("莊家 (B) 總局數", min_value=0, value=st.session_state.b_count)
    st.session_state.p_count = st.number_input("閒家 (P) 總局數", min_value=0, value=st.session_state.p_count)
    st.session_state.t_count = st.number_input("和局 (T) 總局數", min_value=0, value=st.session_state.t_count)

    st.markdown("---")
    if st.button("⚡ 手動強制運行 AI 模擬", type="primary", use_container_width=True):
        trigger_calc = True
    
    if st.button("🔄 本靴洗牌 / 重置數據", use_container_width=True):
        st.session_state.b_count = 0
        st.session_state.p_count = 0
        st.session_state.t_count = 0
        st.rerun()

# -------------------- 右側欄：數據顯示終端與回測系統 --------------------
with right_column:
    tab1, tab2 = st.tabs(["🔮 當前局即時預測", "📈 注碼歷史盈利模擬器"])
    
    # 【分頁 1：當前局即時預測】
    with tab1:
        total_hands = st.session_state.b_count + st.session_state.p_count + st.session_state.t_count
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="🎰 已開局數", value=total_hands)
        with m_col2:
            b_ratio = (st.session_state.b_count / max(1, total_hands) * 100)
            st.metric(label="🔴 莊家開出比例", value=f"{b_ratio:.1f}%")
        with m_col3:
            p_ratio = (st.session_state.p_count / max(1, total_hands) * 100)
            st.metric(label="🔵 閒家開出比例", value=f"{p_ratio:.1f}%")

        st.markdown(" ")
        
        if trigger_calc or total_hands > 0:
            with st.spinner("🧠 雲端正在進行幾萬靴殘牌矩陣運算..."):
                avg_tc, b_prob, p_prob, t_prob, recommend, k_percent, s_bet = run_monte_carlo_with_kelly(
                    st.session_state.b_count, st.session_state.p_count, st.session_state.t_count, 
                    bankroll=total_bankroll, sim_count=sim_runs
                )
                
            if avg_tc is None:
                st.error(recommend)
            else:
                if s_bet > 0:
                    st.markdown(f"""
                    <div style="background-color: #2b2203; padding: 20px; border-left: 5px solid #ffcc00; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="color: #ffcc00; margin: 0;">🔥 AI 決策信號：{recommend}</h3>
                        <p style="color: #ffffff; font-size: 18px; margin: 10px 0 0 0;">
                            💵 <b>建議下注金額： <span style="font-size: 24px; color: #00ffcc;">${s_bet}</span></b> 
                            （佔總資金 {k_percent:.2f}%，已自動套用 1/4 安全凱利注碼）
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background-color: #14211a; padding: 20px; border-left: 5px solid #28a745; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="color: #28a745; margin: 0;">💤 AI 決策信號：{recommend}</h3>
                        <p style="color: #cccccc; margin: 10px 0 0 0;">當前牌靴剩餘組合期望值為負，未產生統計學邊際優勢，請維持觀望磨損賭場。</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("#### 📊 下一局精確概率矩陣")
                data_matrix = {
                    "核心數據指標": ["預估鞋牌真值 (True Count)", "下一局開【莊】修正勝率", "下一局開【閒】修正勝率", "下一局開【和】預測概率"],
                    "即時數值": [f"{avg_tc:.2f}", f"{b_prob:.2f}%", f"{p_prob:.2f}%", f"{t_prob:.2f}%"],
                    "量化統計學解讀說明": [
                        "大於 0 利閒，小於 0 利莊。絕對值大於 10 為極端大優勢訊號。",
                        "已根據剩餘扣牌點數精確修正後的真實莊家開出勝率（未扣 5% 抽水）。",
                        "已根據剩餘扣牌點數精確修正後的真實閒家開出勝率（1賠1無抽水）。",
                        "百家樂和局補牌規則極度固定，受殘牌點數算牌影響極微。"
                    ]
                }
                st.table(pd.DataFrame(data_matrix))
                
                st.markdown("#### 🔮 開牌勝率視覺化走勢")
                st.progress(b_prob / 100, text=f"🔴 莊家 (Banker) 勝率: {b_prob:.2f}%")
                st.progress(p_prob / 100, text=f"🔵 閒家 (Player) 勝率: {p_prob:.2f}%")
        else:
            st.info("💡 請在左側輸入或在側邊欄開啟自動抓取，系統將實時輸出決策。")

    # 【分頁 2：注碼歷史盈利模擬器】
    with tab2:
        st.markdown("### 📊 批量路單凱利回測系統")
        st.write("請在下方輸入或貼上整靴牌的歷史結果，系統將模擬從第一局開始，完全遵循凱利公式的資產走勢。")
        
        default_road = "莊,莊,閒,莊,和,閒,閒,莊,閒,莊,莊,莊,閒,和,閒,莊,閒,閒,莊,莊,閒,莊,莊,莊,閒,閒,莊"
        user_road_input = st.text_area("歷史路單（支援「莊/閒/和」或「B/P/T」，用英文逗號或換行隔開）", value=default_road, height=100)
        
        if st.button("🚀 開始動態盈利曲線模擬回測", use_container_width=True):
            cleaned_road = []
            raw_items = [item.strip() for item in user_road_input.replace("\n", ",").split(",") if item.strip()]
            for item in raw_items:
                if item in ['莊', 'B', 'b', 'Banker']: cleaned_road.append('B')
                elif item in ['閒', 'P', 'p', 'Player']: cleaned_road.append('P')
                elif item in ['和', 'T', 't', 'Tie']: cleaned_road.append('T')
            
            if len(cleaned_road) < 3:
                st.error("❌ 輸入的路單數據局數過少，無法生成趨勢圖表。")
            else:
                current_sim_bankroll = total_bankroll
                bankroll_history = [current_sim_bankroll]
                b_tracker, p_tracker, t_tracker = 0, 0, 0
                trade_logs = []
                
                for i, actual_result in enumerate(cleaned_road):
                    avg_tc, b_prob, p_prob, t_prob, recommend, k_percent, s_bet = run_monte_carlo_with_kelly(
                        b_tracker, p_tracker, t_tracker, bankroll=current_sim_bankroll, sim_count=5000
                    )
                    
                    bet_type, bet_amount, profit = "無", 0, 0
                    if s_bet > 0:
                        bet_amount = s_bet
                        if "【莊】" in recommend:
                            bet_type = "莊"
                            profit = int(bet_amount * 0.95) if actual_result == 'B' else (-bet_amount if actual_result == 'P' else 0)
                        elif "【閒】" in recommend:
                            bet_type = "閒"
                            profit = bet_amount if actual_result == 'P' else (-bet_amount if actual_result == 'B' else 0)
                    
                    current_sim_bankroll += profit
                    bankroll_history.append(current_sim_bankroll)
                    
                    if actual_result == 'B': b_tracker += 1
                    elif actual_result == 'P': p_tracker += 1
                    elif actual_result == 'T': t_tracker += 1
                    
                    trade_logs.append({
                        "局數": i + 1,
                        "開牌": actual_result,
                        "建議下注": bet_type,
                        "下注金額 ($)": bet_amount,
                        "本局損益 ($)": profit,
                        "賬戶結餘 ($)": current_sim_bankroll
                    })

                st.subheader("📈 資金資產增長曲線")
                st.line_chart(bankroll_history)
                
                st.subheader("📜 逐局回測明細")
                st.dataframe(pd.DataFrame(trade_logs), hide_index=True)