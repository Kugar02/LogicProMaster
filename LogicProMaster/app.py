import statistics

import pandas as pd
import streamlit as st

try:
    from engine import get_engine_diagnostics, run_monte_carlo_with_kelly
except ImportError:
    get_engine_diagnostics = None
    run_monte_carlo_with_kelly = None

st.set_page_config(
    page_title="Quantum Baccarat Dynamic OS",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: .8rem !important; max-width: 98% !important; }
    .stButton>button { height: 46px; font-size: 16px; font-weight: bold; }
    .pattern-card { background:#1e2029; border:1px solid #333644; border-radius:8px; padding:12px; margin-bottom:8px; }
    .weight-box { background:#0f1015; border:2px solid #00ffcc; padding:15px; border-radius:10px; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

for key, default in (
    ("history", []),
    ("ai_targets", []),
    ("bankroll", 10000),
    ("base_unit", 100),
    ("strategy", "信號強弱 (1-2-3)"),
):
    if key not in st.session_state:
        st.session_state[key] = default


def auto_window_alpha(history):
    values = [1 if x == "B" else 0 for x in history if x in ("B", "P")]
    n = len(values)
    window = 30 if n < 30 else min(100, max(30, n // 2))
    sample = values[-window:]
    volatility = statistics.pstdev(sample) if len(sample) > 1 else 0.25
    alpha = round(min(0.5, max(0.05, 0.10 + volatility * 1.5)), 3)
    return window, alpha


def build_logical_columns(history):
    columns, current, last = [], [], None
    for result in history:
        if result == "T":
            continue
        if result != last:
            if current:
                columns.append(current)
            current, last = [result], result
        else:
            current.append(result)
    if current:
        columns.append(current)
    return columns


def get_derived_road(columns, k):
    derived = []
    for c in range(1, len(columns)):
        for r in range(len(columns[c])):
            if c < k:
                continue
            if r == 0:
                if c < k + 1:
                    continue
                derived.append(
                    "Red" if len(columns[c - 1]) == len(columns[c - 1 - k]) else "Blue"
                )
            else:
                reference = len(columns[c - k])
                if reference >= r + 1 or reference < r:
                    derived.append("Red")
                else:
                    derived.append("Blue")
    return derived


def layout_road_matrix(items, rows=6):
    grid = {}
    column = row = start_column = 0
    last_value = None
    for item in items:
        value = item["val"] if isinstance(item, dict) else item
        if last_value is None:
            last_value = value
            grid[(column, row)] = item
        elif value == last_value:
            row += 1
            if row >= rows or (column, row) in grid:
                row -= 1
                column += 1
            grid[(column, row)] = item
        else:
            last_value = value
            start_column += 1
            column = start_column
            while (column, 0) in grid:
                column += 1
            start_column = column
            row = 0
            grid[(column, row)] = item
    return grid


def render_css_grid(grid, rows=6, cols=30, cell_size=24, road_type="big"):
    html = (
        '<div style="display:grid;grid-template-columns:repeat({},{}px);'
        'grid-template-rows:repeat({},{}px);background:#fff;border:1px solid #ccc;'
        'width:max-content;">'
    ).format(cols, cell_size, rows, cell_size)

    for row in range(rows):
        for column in range(cols):
            cell = grid.get((column, row))
            content = ""
            if cell is not None:
                value = cell["val"] if isinstance(cell, dict) else cell
                ties = cell.get("ties", 0) if isinstance(cell, dict) else 0
                color = "#e81123" if value in ("B", "Red") else "#0078d7" if value in ("P", "Blue") else "#2ca02c"
                if road_type == "bead":
                    background = "#e81123" if value == "B" else "#0078d7" if value == "P" else "#2ca02c"
                    text = "莊" if value == "B" else "閒" if value == "P" else "和"
                    content = (
                        '<div style="width:20px;height:20px;background:{};color:white;'
                        'border-radius:50%;font-size:10px;line-height:20px;text-align:center;'
                        'margin:auto;font-weight:bold;">{}</div>'
                    ).format(background, text)
                elif road_type == "big":
                    content = '<div style="width:16px;height:16px;border:2px solid {};border-radius:50%;margin:auto;">'.format(color)
                    if ties:
                        content += '<div style="position:absolute;width:20px;height:2px;background:#2ca02c;transform:rotate(-45deg);top:7px;left:-4px;"></div>'
                    content += "</div>"
                elif road_type == "big_eye":
                    content = '<div style="width:12px;height:12px;border:2px solid {};border-radius:50%;margin:auto;"></div>'.format(color)
                elif road_type == "small":
                    content = '<div style="width:12px;height:12px;background:{};border-radius:50%;margin:auto;"></div>'.format(color)
                elif road_type == "roach":
                    content = '<div style="width:16px;height:3px;background:{};transform:rotate(-45deg);margin:auto;margin-top:8px;"></div>'.format(color)
            html += '<div style="border:1px solid #eee;display:flex;align-items:center;justify-content:center;">{}</div>'.format(content)
    return '<div style="overflow-x:auto;padding-bottom:10px;">{}</div>'.format(html + "</div>")


def draw_ask_icon(value, kind):
    if not value:
        return "<div style='width:18px;height:18px;'></div>"
    color = "#e81123" if value == "Red" else "#0078d7"
    if kind == "eye":
        return '<div style="width:14px;height:14px;border:2px solid {};border-radius:50%;"></div>'.format(color)
    if kind == "small":
        return '<div style="width:14px;height:14px;background:{};border-radius:50%;"></div>'.format(color)
    return '<div style="width:14px;height:3px;background:{};transform:rotate(-45deg);"></div>'.format(color)


history = st.session_state.history
window, alpha = auto_window_alpha(history)
b_count, p_count, t_count = history.count("B"), history.count("P"), history.count("T")
total_hands = len(history)

# Evaluate existing bets before calculating the next recommendation.
fibo_idx = double_dragon_idx = 0
tumbler_unit = 1
total_bets = wins = losses = 0
pnl = 0.0
for target_record, actual in zip(st.session_state.ai_targets, history):
    if target_record and target_record.get("target") and actual != "T":
        total_bets += 1
        amount = target_record.get("amount", 0)
        if target_record["target"] == actual:
            wins += 1
            pnl += amount * 0.95 if actual == "B" else amount
            fibo_idx = max(0, fibo_idx - 2)
            double_dragon_idx = 0
            tumbler_unit = min(3, tumbler_unit + 1) if tumbler_unit < 3 else 1
        else:
            losses += 1
            pnl -= amount
            fibo_idx += 1
            double_dragon_idx += 1
            tumbler_unit = 1

current_bet = 0
target = None
recommend = "數據準備中..."
roads = {}
is_break_active = False
consecutive_losses = 0
status = ""
resonance = False
confidence = 50
final_b = final_p = 45.8
actual_t_ratio = 9.5
signal_level = "弱訊號"

if total_hands and run_monte_carlo_with_kelly:
    try:
        result = run_monte_carlo_with_kelly(
            b_count, p_count, t_count,
            bankroll=st.session_state.bankroll,
            sim_count=0,
            history_list=history,
            ai_targets=st.session_state.ai_targets,
            window=window,
            alpha=alpha,
        )
    except TypeError:
        result = run_monte_carlo_with_kelly(
            b_count, p_count, t_count,
            bankroll=st.session_state.bankroll,
            sim_count=0,
            history_list=history,
            ai_targets=st.session_state.ai_targets,
        )

    if len(result) >= 13:
        _, final_b, final_p, actual_t_ratio, recommend, roads, is_break_active, consecutive_losses, status, resonance, confidence, signal_level, _ = result
    else:
        (_, final_b, final_p, actual_t_ratio, recommend, roads, is_break_active,
         consecutive_losses, status, resonance, confidence) = result[:11]
        signal_level = "強訊號" if confidence >= 75 else "中訊號" if confidence >= 50 else "弱訊號"

    target = "B" if "莊" in recommend else "P" if "閒" in recommend else None
    if target:
        if st.session_state.strategy == "信號強弱 (1-2-3)":
            multiplier = {"強訊號": 2.0, "中訊號": 1.0, "弱訊號": 0.5}.get(signal_level, 1.0)
            current_bet = max(1, round(st.session_state.base_unit * multiplier))
        elif st.session_state.strategy == "斐波那契 (Fibonacci)":
            sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
            current_bet = st.session_state.base_unit * sequence[min(fibo_idx, len(sequence) - 1)]
        elif st.session_state.strategy == "雙頭龍":
            sequence = [1, 1, 2, 2, 4, 4, 8, 8, 16, 16, 32, 32]
            current_bet = st.session_state.base_unit * sequence[min(double_dragon_idx, len(sequence) - 1)]
        else:
            current_bet = st.session_state.base_unit * tumbler_unit

# ================= 資金管理 + 輸入並列 =================
st.markdown("### ⚙️ 資金管理與牌局輸入")
left, right = st.columns([2, 1.25])
with left:
    c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
    st.session_state.bankroll = c1.number_input("💰 本金 ($)", min_value=100, value=st.session_state.bankroll, step=500)
    st.session_state.base_unit = c2.number_input("💵 基礎注碼 ($)", min_value=10, value=st.session_state.base_unit, step=10)
    st.session_state.strategy = c3.selectbox("📈 注碼策略", ["信號強弱 (1-2-3)", "斐波那契 (Fibonacci)", "雙頭龍", "不倒翁投注法"])
    st.info(f"策略：{st.session_state.strategy} ｜ 下一注：${current_bet} ｜ AI訊號：{signal_level}")
with right:
    st.markdown("##### 🎛️ 開牌輸入")
    buttons = st.columns(4)

    def record_hand(result):
        st.session_state.ai_targets.append({"target": target, "amount": current_bet} if target else None)
        st.session_state.history.append(result)
        st.rerun()

    if buttons[0].button("🔴 B", use_container_width=True): record_hand("B")
    if buttons[1].button("🔵 P", use_container_width=True): record_hand("P")
    if buttons[2].button("🟢 T", use_container_width=True): record_hand("T")
    if buttons[3].button("↩️ 撤銷", use_container_width=True):
        if history:
            st.session_state.history.pop()
            st.session_state.ai_targets.pop()
        st.rerun()
    if st.button("🗑️ 清空重置（新靴）", use_container_width=True):
        st.session_state.history = []
        st.session_state.ai_targets = []
        st.rerun()
    with st.expander("📝 批量輸入"):
        batch = st.text_input("例如 BBPTP...", key="batch_input")
        if st.button("📥 載入歷史", use_container_width=True):
            cleaned = []
            for char in batch:
                if char in "Bb莊庄": cleaned.append("B")
                elif char in "Pp閒闲": cleaned.append("P")
                elif char in "Tt和": cleaned.append("T")
            if cleaned:
                st.session_state.history.extend(cleaned)
                st.session_state.ai_targets.extend([None] * len(cleaned))
                st.rerun()

st.markdown("#### 📋 最終權重及下注統計")
win_rate = wins / total_bets * 100 if total_bets else 0.0
st.write(f"最終權重：莊 {final_b:.1f}% ｜ 閒 {final_p:.1f}% ｜ 可信度 {confidence}% ｜ {signal_level}")
st.write(f"下注：{total_bets} 次 ｜ 勝 {wins} ｜ 負 {losses} ｜ 實際勝率 {win_rate:.1f}%")
st.write(f"本金：${st.session_state.bankroll:.2f} ｜ 策略損益：${pnl:.2f} ｜ 含本金資產：${st.session_state.bankroll + pnl:.2f}")

if total_hands:
    st.markdown("### 🧠 最終權重預測建議")
    st.markdown(f'<div class="weight-box"><h2>{recommend}</h2><p>莊 {final_b:.1f}% ｜ 閒 {final_p:.1f}% ｜ 訊號：{signal_level}</p><small>{status}</small></div>', unsafe_allow_html=True)
    if is_break_active:
        st.warning(f"反打機制生效：最近連敗 {consecutive_losses} 局。")

if roads:
    st.markdown("#### 🔍 四大核心診斷")
    road_columns = st.columns(4)
    for column, item in zip(road_columns, roads.values()):
        ranking = item.get("feature_ranking", [])
        features = " ｜ ".join(f"{x['feature']} {x['value']:+.1f}" for x in ranking) or "沒有足夠特徵"
        with column:
            st.markdown(f'<div class="pattern-card"><b>{item.get("name", "核心")}</b><br>{item.get("status", "")}<br><small>{features}</small></div>', unsafe_allow_html=True)

st.markdown("### 📊 專業娛樂城路紙（五路全開）")
big_road = []
for item in history:
    if item == "T" and big_road:
        big_road[-1]["ties"] += 1
    elif item != "T":
        big_road.append({"val": item, "ties": 0})

logical = build_logical_columns(history)
road_top_left, road_top_right = st.columns([1, 2])
with road_top_left:
    st.caption("珠盤路")
    bead = {(i // 6, i % 6): value for i, value in enumerate(history)}
    st.markdown(render_css_grid(bead, cols=12, cell_size=28, road_type="bead"), unsafe_allow_html=True)
with road_top_right:
    st.caption("大路")
    st.markdown(render_css_grid(layout_road_matrix(big_road), cols=30, cell_size=28), unsafe_allow_html=True)

st.caption("下三路")
for column, k, road_type in zip(st.columns(3), (1, 2, 3), ("big_eye", "small", "roach")):
    with column:
        st.markdown(render_css_grid(layout_road_matrix(get_derived_road(logical, k)), cols=24, cell_size=18, road_type=road_type), unsafe_allow_html=True)

ask_b = [get_derived_road(build_logical_columns(history + ["B"]), k) for k in (1, 2, 3)]
ask_p = [get_derived_road(build_logical_columns(history + ["P"]), k) for k in (1, 2, 3)]
st.markdown("#### 問路")
st.write("莊問路：" + " / ".join(x[-1] if x else "-") for x in ask_b)
st.write("閒問路：" + " / ".join(x[-1] if x else "-") for x in ask_p)

if total_hands and get_engine_diagnostics:
    with st.expander("📈 牌靴波動圖", expanded=False):
        points = get_engine_diagnostics(history, st.session_state.ai_targets, window, alpha)
        if points:
            chart = pd.DataFrame(points).set_index("局數")
            st.line_chart(chart)
