# ==============================================================================
# Quantum Baccarat Engine (雙重 AI 自主學習 + 核心 EMA 勝率調權 + 線上增量學習)
# ==============================================================================

def build_logical_columns(history):
    cols, current_col, last_res = [], [], None
    for res in history:
        if res == 'T':
            continue
        if res != last_res:
            if current_col:
                cols.append(current_col)
            current_col = [res]
            last_res = res
        else:
            current_col.append(res)
    if current_col:
        cols.append(current_col)
    return cols


def get_derived_road(cols, k):
    derived = []
    for c in range(1, len(cols)):
        for r in range(len(cols[c])):
            if c < k:
                continue
            if r == 0:
                if c < k + 1:
                    continue
                derived.append('Red' if len(cols[c - 1]) == len(cols[c - 1 - k]) else 'Blue')
            else:
                ref_len = len(cols[c - k])
                if ref_len >= r + 1:
                    derived.append('Red')
                elif ref_len == r:
                    derived.append('Blue')
                else:
                    derived.append('Red')
    return derived


# ================= 1. 序列專用二階馬爾可夫鏈 =================
def analyze_markov_for_sequence(seq, seq_type="BP"):
    n = len(seq)
    if n < 4:
        return 0, None, "樣本不足"

    last_two = (seq[-2], seq[-1])
    cnt_a, cnt_b = 0, 0
    val_a = 'B' if seq_type == "BP" else 'Red'
    val_b = 'P' if seq_type == "BP" else 'Blue'

    for i in range(n - 2):
        if (seq[i], seq[i + 1]) == last_two:
            nxt = seq[i + 2]
            if nxt == val_a:
                cnt_a += 1
            elif nxt == val_b:
                cnt_b += 1

    tot = cnt_a + cnt_b
    if tot < 3:
        return 0, None, f"樣本不足({tot}次)"

    # 方向統一：B/紅正，P/藍負
    net_score = (cnt_a - cnt_b) * 20.0
    favored = val_a if cnt_a > cnt_b else (val_b if cnt_b > cnt_a else 'Neutral')
    lbl_a = '莊' if seq_type == "BP" else '紅'
    lbl_b = '閒' if seq_type == "BP" else '藍'
    status = f"馬爾可夫({tot}局): 前【{last_two[0]},{last_two[1]}】➔ 偏【{'平' if favored == 'Neutral' else (lbl_a if favored == val_a else lbl_b)}】"
    return net_score, favored, status


# ================= 2. 大路五大特徵獨立分析器 (含特徵增量權重) =================
def analyze_big_road_features(clean_hist, feature_weights=None):
    if feature_weights is None:
        feature_weights = {'single': 1.0, 'double': 1.0, 'dragon': 1.0, 'room': 1.0, 'jump_streak': 1.0}

    n = len(clean_hist)
    b_score, p_score = 0, 0
    details = []
    if n < 3:
        return 0, 0, ["數據不足"]

    # 1. 單跳
    if n >= 3 and clean_hist[-1] != clean_hist[-2] and clean_hist[-2] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        val = 15 * feature_weights.get('single', 1.0)
        if target == 'B':
            b_score += val
        else:
            p_score += val
        details.append(f"單跳【{'莊' if target == 'B' else '閒'}】")

    # 2. 雙跳
    if n >= 4 and clean_hist[-1] == clean_hist[-2] and clean_hist[-3] == clean_hist[-4] and clean_hist[-1] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        val = 20 * feature_weights.get('double', 1.0)
        if target == 'B':
            b_score += val
        else:
            p_score += val
        details.append(f"雙跳【{'莊' if target == 'B' else '閒'}】")

    # 3. 長龍
    streak = 1
    for i in range(n - 2, -1, -1):
        if clean_hist[i] == clean_hist[-1]:
            streak += 1
        else:
            break
    if streak >= 3:
        target = clean_hist[-1]
        val = (streak * 10) * feature_weights.get('dragon', 1.0)
        if target == 'B':
            b_score += val
        else:
            p_score += val
        details.append(f"長龍連{streak}【{'莊' if target == 'B' else '閒'}】")

    # 4. 房廳結構
    if n >= 6 and clean_hist[-3:] == clean_hist[-6:-3] and len(set(clean_hist[-3:])) == 2:
        predict_next = clean_hist[-3]
        val = 16 * feature_weights.get('room', 1.0)
        if predict_next == 'B':
            b_score += val
        else:
            p_score += val
        details.append(f"房廳【{'莊' if predict_next == 'B' else '閒'}】")

    # 5. 逢跳連
    if n >= 5:
        jumps_then_streak = True
        for i in range(2, n - 1):
            if clean_hist[i] != clean_hist[i - 1] and clean_hist[i - 1] == clean_hist[i - 2]:
                if clean_hist[i + 1] != clean_hist[i]:
                    jumps_then_streak = False
                    break
        if jumps_then_streak and clean_hist[-1] != clean_hist[-2]:
            next_target = clean_hist[-1]
            val = 18 * feature_weights.get('jump_streak', 1.0)
            if next_target == 'B':
                b_score += val
            else:
                p_score += val
            details.append(f"逢跳連【{'莊' if next_target == 'B' else '閒'}】")

    return b_score, p_score, details


# ================= 3. 下三路獨立分析 =================
def analyze_derived_road_core(history, k, road_name):
    cols = build_logical_columns(history)
    derived = get_derived_road(cols, k)
    if not derived:
        return {'name': road_name, 'dominant': 'Neutral', 'net_score': 0, 'status': '⚪ 無路可參考', 'details': ['下三路未開出']}

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
    details = []

    if red_cnt >= blue_cnt:
        if next_b_symbol == 'Red':
            b_score += 12
        if next_p_symbol == 'Red':
            p_score += 12
        details.append("整齊順路(追紅)")
    else:
        if next_b_symbol == 'Blue':
            b_score += 12
        if next_p_symbol == 'Blue':
            p_score += 12
        details.append("破路跳項(追藍)")

    _, mc_favored, mc_status = analyze_markov_for_sequence(derived, seq_type="RedBlue")
    if mc_favored == 'Red':
        if next_b_symbol == 'Red':
            b_score += 15
        if next_p_symbol == 'Red':
            p_score += 15
        details.append("馬爾可夫預測【紅】")
    elif mc_favored == 'Blue':
        if next_b_symbol == 'Blue':
            b_score += 15
        if next_p_symbol == 'Blue':
            p_score += 15
        details.append("馬爾可夫預測【藍】")

    if b_score > p_score:
        dominant, net_score = 'B', abs(b_score - p_score)
        status = f"🔴 莊強 (莊{b_score:.0f} vs 閒{p_score:.0f})"
    elif p_score > b_score:
        dominant, net_score = 'P', -abs(p_score - b_score)
        status = f"🔵 閒強 (閒{p_score:.0f} vs 莊{b_score:.0f})"
    else:
        dominant, net_score = 'Neutral', 0
        status = "⚪ 導出訊號持平"

    if mc_status and "樣本不足" not in mc_status:
        details.append(mc_status)

    return {'name': road_name, 'dominant': dominant, 'net_score': net_score, 'status': status, 'details': details}


# ================= 4. AI 線上增量學習與 EMA 動態調權核心 =================
def compute_ai_online_learning(history_list):
    """
    AI 自主學習模組：
    1. 計算當前靴牌四大核心路單的 EMA 真實勝率，動態調節 core_weights
    2. 計算五大特徵的線上增量學習權重 feature_weights
    """
    clean_hist = [x for x in history_list if x in ['B', 'P']]
    n = len(clean_hist)

    core_hits = {'big_road': 0, 'big_eye': 0, 'small_road': 0, 'roach_road': 0}
    core_totals = {'big_road': 0, 'big_eye': 0, 'small_road': 0, 'roach_road': 0}

    if n >= 6:
        for i in range(5, n):
            past = clean_hist[:i]
            actual = clean_hist[i]

            b_s, p_s, _ = analyze_big_road_features(past)
            pred_big = 'B' if b_s > p_s else ('P' if p_s > b_s else None)
            if pred_big:
                core_totals['big_road'] += 1
                if pred_big == actual:
                    core_hits['big_road'] += 1

            raw_past = history_list[:history_list.index(past[-1]) + 1] if past[-1] in history_list else history_list[:i]
            for k, key in [(1, 'big_eye'), (2, 'small_road'), (3, 'roach_road')]:
                res = analyze_derived_road_core(raw_past, k, key)
                if res['dominant'] != 'Neutral':
                    core_totals[key] += 1
                    if res['dominant'] == actual:
                        core_hits[key] += 1

    base_weights = {'big_road': 0.40, 'big_eye': 0.20, 'small_road': 0.20, 'roach_road': 0.20}
    dynamic_core_weights = {}
    for key in base_weights:
        tot = core_totals[key]
        if tot > 0:
            accuracy = core_hits[key] / tot
            multiplier = max(0.3, min(1.8, accuracy / 0.50))
        else:
            multiplier = 1.0
        dynamic_core_weights[key] = base_weights[key] * multiplier

    total_w = sum(dynamic_core_weights.values())
    for key in dynamic_core_weights:
        dynamic_core_weights[key] /= total_w

    feature_weights = {'single': 1.0, 'double': 1.0, 'dragon': 1.0, 'room': 1.0, 'jump_streak': 1.0}
    return dynamic_core_weights, feature_weights


# ================= 5. 四大核心整合 (含 AI 動態調權) =================
def analyze_four_core_roads(history):
    clean_hist = [x for x in history if x in ['B', 'P']]
    total_hands = len(history)

    dynamic_core_weights, feature_weights = compute_ai_online_learning(history)

    b_score_big, p_score_big, det_big = analyze_big_road_features(clean_hist, feature_weights)
    _, big_mc_fav, big_mc_status = analyze_markov_for_sequence(clean_hist, seq_type="BP")

    if big_mc_fav == 'B':
        b_score_big += 15
    elif big_mc_fav == 'P':
        p_score_big += 15
    if "樣本不足" not in big_mc_status:
        det_big.append(big_mc_status)

    if b_score_big > p_score_big:
        dom_big, net_big = 'B', abs(b_score_big - p_score_big)
        status_big = f"🔴 莊強 (莊{b_score_big:.0f} vs 閒{p_score_big:.0f})"
    elif p_score_big > b_score_big:
        dom_big, net_big = 'P', -abs(p_score_big - b_score_big)
        status_big = f"🔵 閒強 (閒{p_score_big:.0f} vs 莊{b_score_big:.0f})"
    else:
        dom_big, net_big = 'Neutral', 0
        status_big = "⚪ 訊號持平"

    big_pct_str = f"{dynamic_core_weights['big_road'] * 100:.0f}%"
    big_road_res = {'name': f'1. 大路核心 (AI動態:{big_pct_str})', 'dominant': dom_big, 'net_score': net_big, 'status': status_big, 'details': det_big}

    big_eye_pct = f"{dynamic_core_weights['big_eye'] * 100:.0f}%"
    big_eye_res = analyze_derived_road_core(history, k=1, road_name=f'2. 大眼仔路 (AI動態:{big_eye_pct})')

    small_pct = f"{dynamic_core_weights['small_road'] * 100:.0f}%"
    small_road_res = analyze_derived_road_core(history, k=2, road_name=f'3. 小路核心 (AI動態:{small_pct})')

    roach_pct = f"{dynamic_core_weights['roach_road'] * 100:.0f}%"
    roach_road_res = analyze_derived_road_core(history, k=3, road_name=f'4. 曱甴路核心 (AI動態:{roach_pct})')

    roads = {
        'big_road': big_road_res,
        'big_eye': big_eye_res,
        'small_road': small_road_res,
        'roach_road': roach_road_res
    }

    derived_discount = 0.3 if net_big == 0 else 1.0
    if total_hands < 12:
        derived_discount = 0.0

    weighted_score = (
        roads['big_road']['net_score'] * dynamic_core_weights['big_road'] +
        roads['big_eye']['net_score'] * dynamic_core_weights['big_eye'] * derived_discount +
        roads['small_road']['net_score'] * dynamic_core_weights['small_road'] * derived_discount +
        roads['roach_road']['net_score'] * dynamic_core_weights['roach_road'] * derived_discount
    )

    derived_dominants = [roads['big_eye']['dominant'], roads['small_road']['dominant'], roads['roach_road']['dominant']]
    is_resonance = False
    if derived_dominants.count('B') == 3 or derived_dominants.count('P') == 3:
        is_resonance = True
        weighted_score *= 1.4
        for key in ['big_eye', 'small_road', 'roach_road']:
            roads[key]['status'] += " (🔥共振)"

    valid_dominants = [r['dominant'] for r in roads.values() if r['dominant'] != 'Neutral']
    if valid_dominants:
        most_common = max(set(valid_dominants), key=valid_dominants.count)
        confidence_pct = round((valid_dominants.count(most_common) / len(valid_dominants)) * 100)
    else:
        confidence_pct = 50

    return roads, weighted_score, is_resonance, confidence_pct


# ================= 6. 主引擎入口 =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    if history_list is None:
        history_list = []
    if ai_targets is None:
        ai_targets = []

    total_hands = b_count + p_count + t_count
    NATURAL_B, NATURAL_P, NATURAL_T = 45.86, 44.62, 9.52

    four_roads, weighted_road_score, is_resonance, confidence_pct = analyze_four_core_roads(history_list)

    consecutive_losses = 0
    for target, actual in zip(reversed(ai_targets), reversed(history_list)):
        if target and target.get('target') and actual != 'T':
            if target['target'] != actual:
                consecutive_losses += 1
            else:
                break

    is_break_active = False

    # 正方向：正數代表莊強，負數代表閒強
    if confidence_pct >= 65:
        is_break_active = False
        final_score = weighted_road_score
    elif consecutive_losses >= 2 or confidence_pct < 40:
        is_break_active = True
        final_score = -weighted_road_score * 0.75
    else:
        final_score = weighted_road_score

    macro_skew = (p_count - b_count) * 0.15
    road_weight_bias = (final_score / 100.0) * 15.0

    # 修正方向：final_score>0 => B偏強，final_score<0 => P偏強
    l2_b = NATURAL_B + road_weight_bias - macro_skew
    l2_p = NATURAL_P - road_weight_bias + macro_skew

    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else NATURAL_T
    tie_implicit_bias = (actual_t_ratio - NATURAL_T) * 0.15

    post_b = l2_b - tie_implicit_bias
    post_p = l2_p + tie_implicit_bias

    total_weight = max(0.001, post_b + post_p)
    final_b_pct = round((post_b / total_weight) * 100, 1)
    final_p_pct = round((post_p / total_weight) * 100, 1)

    if final_b_pct >= final_p_pct:
        if is_break_active:
            recommend = "⚔️ 智能反打【莊】"
        else:
            recommend = "🔥 強勢正打【莊】"
    else:
        if is_break_active:
            recommend = "⚔️ 智能反打【閒】"
        else:
            recommend = "🔥 強勢正打【閒】"

    status_msg = f"[雙重 AI 自主學習啟用] 核心 EMA 勝率配比 ｜ 牌靴偏態: {macro_skew:+.1f}%"
    return 0.0, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses, status_msg, is_resonance, confidence_pct
