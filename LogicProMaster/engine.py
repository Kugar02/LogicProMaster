# ==============================================================================
# Quantum Baccarat Engine (5大極致精準優化版 - 無蒙地卡羅)
# 1. 牌靴冷啟動 (前11局下三路權重0)
# 2. 大路權威門閥 (大路無訊號時下三路權重打3折)
# 3. 馬爾可夫鏈樣本門檻 (tot >= 3 才採計)
# 4. 下三路紅藍規律語意修復 (直接評估整齊度/跳路)
# 5. 破路連爆動態風控門閥 (提升進場門檻至 53.5%)
# ==============================================================================

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

# ================= 1. 大路五大特徵獨立分析器 =================
def analyze_big_road_features(clean_hist):
    """專門針對大路 B/P 序列分析五大特徵"""
    n = len(clean_hist)
    b_score, p_score = 0, 0
    details = []
    if n < 3: return 0, 0, ["數據不足 (需至少3局)"]

    # 1. 單跳 (B-P-B-P...)
    if n >= 3 and clean_hist[-1] != clean_hist[-2] and clean_hist[-2] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        if target == 'B': b_score += 15
        else: p_score += 15
        details.append(f"單跳強向【{'莊' if target=='B' else '閒'}】")

    # 2. 雙跳 (BB-PP-BB...)
    if n >= 4 and clean_hist[-1] == clean_hist[-2] and clean_hist[-3] == clean_hist[-4] and clean_hist[-1] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        if target == 'B': b_score += 20
        else: p_score += 20
        details.append(f"雙跳強向【{'莊' if target=='B' else '閒'}】")

    # 3. 長龍 (BBB... 或 PPP...)
    streak = 1
    for i in range(n-2, -1, -1):
        if clean_hist[i] == clean_hist[-1]: streak += 1
        else: break
    if streak >= 3:
        target = clean_hist[-1]
        s = streak * 10
        if target == 'B': b_score += s
        else: p_score += s
        details.append(f"長龍連{streak}【{'莊' if target=='B' else '閒'}】")

    # 4. 房廳結構 (1房2廳 / 2房1廳)
    if n >= 6 and clean_hist[-3:] == clean_hist[-6:-3] and len(set(clean_hist[-3:])) == 2:
        predict_next = clean_hist[-3]
        if predict_next == 'B': b_score += 16
        else: p_score += 16
        details.append(f"房廳週期【{'莊' if predict_next=='B' else '閒'}】")

    # 5. 逢跳連 (跳後必連)
    if n >= 5:
        jumps_then_streak = True
        for i in range(2, n-1):
            if clean_hist[i] != clean_hist[i-1] and clean_hist[i-1] == clean_hist[i-2]:
                if clean_hist[i+1] != clean_hist[i]:
                    jumps_then_streak = False
                    break
        if jumps_then_streak and clean_hist[-1] != clean_hist[-2]:
            next_target = clean_hist[-1]
            if next_target == 'B': b_score += 18
            else: p_score += 18
            details.append(f"逢跳連【{'莊' if next_target=='B' else '閒'}】")

    return b_score, p_score, details

# ================= 2. 下三路規律度分析器 (優化點 3: 語意修復) =================
def analyze_derived_road_regularity(history, k):
    """
    優化點 3：下三路語意修復。
    下三路不硬套大路形態，而是評估紅筆 (整齊齊腳) 與藍筆 (爆路跳路) 的規律度與走向。
    """
    cols = build_logical_columns(history)
    derived = get_derived_road(cols, k)
    if not derived:
        return {'dominant': 'Neutral', 'net_score': 0, 'status': '⚪ 無路可參考', 'details': ['下三路未開出']}

    recent = derived[-6:]
    red_cnt = recent.count('Red')
    blue_cnt = recent.count('Blue')

    cols_b = build_logical_columns(history + ['B'])
    derived_b = get_derived_road(cols_b, k)
    next_b_symbol = derived_b[-1] if derived_b else None

    cols_p = build_logical_columns(history + ['P'])
    derived_p = get_derived_road(cols_p, k)
    next_p_symbol = derived_p[-1] if derived_p else None

    b_score, p_score = 0, 0
    details = [f"近6局: 紅{red_cnt} / 藍{blue_cnt}"]

    if red_cnt >= blue_cnt:
        # 整齊趨勢：追紅筆
        if next_b_symbol == 'Red': b_score += 15
        if next_p_symbol == 'Red': p_score += 15
        details.append("整齊順路 (追紅筆)")
    else:
        # 破路趨勢：追藍筆
        if next_b_symbol == 'Blue': b_score += 15
        if next_p_symbol == 'Blue': p_score += 15
        details.append("破路跳項 (追藍筆)")

    if b_score > p_score:
        dominant, net_score = 'B', -(b_score - p_score)
        status = f"🔴 莊導出整齊 (莊{b_score} vs 閒{p_score})"
    elif p_score > b_score:
        dominant, net_score = 'P', (p_score - b_score)
        status = f"🔵 閒導出整齊 (閒{p_score} vs 莊{b_score})"
    else:
        dominant, net_score = 'Neutral', 0
        status = "⚪ 導出訊號持平"

    return {'dominant': dominant, 'net_score': net_score, 'status': status, 'details': details}

# ================= 3. 馬爾可夫鏈分析器 (優化點 2: 樣本門檻 tot >= 3) =================
def analyze_markov_chain(history):
    clean_hist = [x for x in history if x in ['B', 'P']]
    n = len(clean_hist)
    if n < 5: return 0, "馬爾可夫數據不足 (總局數<5)"

    last_two = (clean_hist[-2], clean_hist[-1])
    b_next_cnt, p_next_cnt = 0, 0

    for i in range(n - 2):
        if (clean_hist[i], clean_hist[i+1]) == last_two:
            next_val = clean_hist[i+2]
            if next_val == 'B': b_next_cnt += 1
            elif next_val == 'P': p_next_cnt += 1

    tot = b_next_cnt + p_next_cnt

    # 🌟 優化點 2：設定最低顯著樣本門檻 (tot >= 3)
    if tot < 3:
        return 0, f"馬爾可夫樣本不足 (前【{last_two[0]}{last_two[1]}】僅出現{tot}次<門檻3)"

    b_prob = b_next_cnt / tot
    p_prob = p_next_cnt / tot
    net_score = (p_prob - b_prob) * 25.0

    pred = "莊" if b_prob > p_prob else ("閒" if p_prob > b_prob else "持平")
    status = f"馬爾可夫轉移 (樣本{tot}次): 前【{last_two[0]}{last_two[1]}】➔ 次開【{pred}】(莊{b_next_cnt}/閒{p_next_cnt})"
    return net_score, status

# ================= 4. 四大核心整合與權威門閥 (優化點 1 & 5) =================
def analyze_four_core_roads(history):
    clean_hist = [x for x in history if x in ['B', 'P']]
    total_hands = len(history)

    # 1. 大路核心分析
    b_score_big, p_score_big, det_big = analyze_big_road_features(clean_hist)
    if b_score_big > p_score_big:
        dom_big, net_big = 'B', -(b_score_big - p_score_big)
        status_big = f"🔴 莊強 (莊{b_score_big} vs 閒{p_score_big})"
    elif p_score_big > b_score_big:
        dom_big, net_big = 'P', (p_score_big - b_score_big)
        status_big = f"🔵 閒強 (閒{p_score_big} vs 莊{b_score_big})"
    else:
        dom_big, net_big = 'Neutral', 0
        status_big = "⚪ 訊號持平"

    big_road_res = {'name': '1. 大路核心 (主軸40%)', 'dominant': dom_big, 'net_score': net_big, 'status': status_big, 'details': det_big}

    # 2. 下三路規律分析 (優化點 3)
    big_eye_res = analyze_derived_road_regularity(history, k=1)
    big_eye_res['name'] = '2. 大眼仔路 (20%)'

    small_road_res = analyze_derived_road_regularity(history, k=2)
    small_road_res['name'] = '3. 小路核心 (20%)'

    roach_road_res = analyze_derived_road_regularity(history, k=3)
    roach_road_res['name'] = '4. 曱甴路核心 (20%)'

    roads = {
        'big_road': big_road_res,
        'big_eye': big_eye_res,
        'small_road': small_road_res,
        'roach_road': roach_road_res
    }

    # 🌟 優化點 5：牌靴冷啟動機制 (前 11 局下三路權重 = 0)
    if total_hands < 12:
        derived_weight = 0.0
        cold_start_msg = " [冷啟動防護期: 局數<12]"
    else:
        derived_weight = 0.20
        cold_start_msg = ""

    # 🌟 優化點 1：大路權威門閥
    # 若大路無訊號 (net_big == 0)，下三路權重打 3 折 (0.3x)，防止雜訊反客為主
    if net_big == 0:
        derived_discount = 0.3
        gate_msg = " [大路無號: 下三路權重打3折]"
    else:
        derived_discount = 1.0
        gate_msg = ""

    effective_derived_weight = derived_weight * derived_discount

    weighted_score = (
        roads['big_road']['net_score'] * 0.40 +
        roads['big_eye']['net_score'] * effective_derived_weight +
        roads['small_road']['net_score'] * effective_derived_weight +
        roads['roach_road']['net_score'] * effective_derived_weight
    )

    # 三路共振爆發檢查
    derived_dominants = [roads['big_eye']['dominant'], roads['small_road']['dominant'], roads['roach_road']['dominant']]
    is_resonance = False
    if derived_dominants.count('B') == 3 or derived_dominants.count('P') == 3:
        is_resonance = True
        weighted_score *= 1.4
        for key in ['big_eye', 'small_road', 'roach_road']:
            roads[key]['status'] += " (🔥共振)"

    # 自信度指數
    valid_dominants = [r['dominant'] for r in roads.values() if r['dominant'] != 'Neutral']
    if valid_dominants:
        most_common = max(set(valid_dominants), key=valid_dominants.count)
        confidence_pct = round((valid_dominants.count(most_common) / len(valid_dominants)) * 100)
    else:
        confidence_pct = 50

    return roads, weighted_score, is_resonance, confidence_pct, cold_start_msg + gate_msg

# ================= 5. 純統計與動態門閥主引擎 =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []

    total_hands = b_count + p_count + t_count
    NATURAL_B, NATURAL_P, NATURAL_T = 45.86, 44.62, 9.52

    # 四大核心（含優化點 1 & 3 & 5）
    four_roads, weighted_road_score, is_resonance, confidence_pct, status_gate_msg = analyze_four_core_roads(history_list)

    # 二階馬爾可夫（含優化點 2）
    markov_score, markov_status = analyze_markov_chain(history_list)

    # 歷史連爆追蹤
    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break

    is_break_active = False
    is_defense_mode = False
    entry_threshold = 51.2 # 預設進場門檻 (%)

    # 🌟 優化點 4：破路連爆動態風控門閥
    # 連爆 >= 2 局時，提升進場門檻至 53.5%，並降低加權偏置
    if consecutive_losses >= 2:
        is_break_active = True
        entry_threshold = 53.5 # 嚴格進場門檻
        final_score = weighted_road_score * 0.5 + markov_score * 0.3
    else:
        final_score = weighted_road_score + markov_score * 0.5

    # 🌟 優化點 5：冷啟動時期門檻微調
    if total_hands < 12:
        entry_threshold = 52.8

    # 計算動態偏置
    road_weight_bias = (final_score / 100.0) * 14.0
    l2_b = NATURAL_B - road_weight_bias
    l2_p = NATURAL_P + road_weight_bias

    # 和局隱性修正
    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else NATURAL_T
    tie_implicit_bias = (actual_t_ratio - NATURAL_T) * 0.15

    post_b = l2_b - tie_implicit_bias
    post_p = l2_p + tie_implicit_bias

    # 最終歸一化 (Normalization)
    total_weight = max(0.001, post_b + post_p)
    final_b_pct = round((post_b / total_weight) * 100, 1)
    final_p_pct = round((post_p / total_weight) * 100, 1)

    recommend = "觀望 (停注)"
    if not is_defense_mode:
        if final_b_pct >= entry_threshold:
            recommend = "建議下注【莊】" + (" (🛡️高門閥)" if is_break_active else "")
        elif final_p_pct >= entry_threshold:
            recommend = "建議下注【閒】" + (" (🛡️高門閥)" if is_break_active else "")

    full_status_msg = f"{markov_status}{status_gate_msg}"
    return 0.0, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses, full_status_msg, is_resonance, confidence_pct
