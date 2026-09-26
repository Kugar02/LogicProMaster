# ==============================================================================
# Quantum Baccarat Engine (AI 自自主動態學習 + 高自信度保護鎖)
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

# ================= 1. 序列專用二階馬爾可夫鏈 =================
def analyze_markov_for_sequence(seq, seq_type="BP"):
    n = len(seq)
    if n < 4: return 0, None, "樣本不足"

    last_two = (seq[-2], seq[-1])
    cnt_a, cnt_b = 0, 0
    val_a = 'B' if seq_type == "BP" else 'Red'
    val_b = 'P' if seq_type == "BP" else 'Blue'

    for i in range(n - 2):
        if (seq[i], seq[i+1]) == last_two:
            nxt = seq[i+2]
            if nxt == val_a: cnt_a += 1
            elif nxt == val_b: cnt_b += 1

    tot = cnt_a + cnt_b
    if tot < 3: return 0, None, f"樣本不足({tot}次)"

    prob_a = cnt_a / tot
    prob_b = cnt_b / tot
    net_score = (prob_b - prob_a) * 20.0

    favored = val_a if cnt_a > cnt_b else (val_b if cnt_b > cnt_a else 'Neutral')
    lbl_a = '莊' if seq_type == "BP" else '紅'
    lbl_b = '閒' if seq_type == "BP" else '藍'
    status = f"馬爾可夫({tot}局): 前【{last_two[0]},{last_two[1]}】➔ 偏【{'平' if favored=='Neutral' else (lbl_a if favored==val_a else lbl_b)}】"
    return net_score, favored, status

# ================= 2. 大路五大特徵分析器 =================
def analyze_big_road_features(clean_hist):
    n = len(clean_hist)
    b_score, p_score = 0, 0
    details = []
    if n < 3: return 0, 0, ["數據不足"]

    if n >= 3 and clean_hist[-1] != clean_hist[-2] and clean_hist[-2] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        if target == 'B': b_score += 15
        else: p_score += 15
        details.append(f"單跳【{'莊' if target=='B' else '閒'}】")

    if n >= 4 and clean_hist[-1] == clean_hist[-2] and clean_hist[-3] == clean_hist[-4] and clean_hist[-1] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        if target == 'B': b_score += 20
        else: p_score += 20
        details.append(f"雙跳【{'莊' if target=='B' else '閒'}】")

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

    if n >= 6 and clean_hist[-3:] == clean_hist[-6:-3] and len(set(clean_hist[-3:])) == 2:
        predict_next = clean_hist[-3]
        if predict_next == 'B': b_score += 16
        else: p_score += 16
        details.append(f"房廳【{'莊' if predict_next=='B' else '閒'}】")

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
        if next_b_symbol == 'Red': b_score += 12
        if next_p_symbol == 'Red': p_score += 12
        details.append("整齊順路(追紅)")
    else:
        if next_b_symbol == 'Blue': b_score += 12
        if next_p_symbol == 'Blue': p_score += 12
        details.append("破路跳項(追藍)")

    mc_score, mc_favored, mc_status = analyze_markov_for_sequence(derived, seq_type="RedBlue")
    if mc_favored == 'Red':
        if next_b_symbol == 'Red': b_score += 15
        if next_p_symbol == 'Red': p_score += 15
        details.append(f"馬爾可夫預測【紅】")
    elif mc_favored == 'Blue':
        if next_b_symbol == 'Blue': b_score += 15
        if next_p_symbol == 'Blue': p_score += 15
        details.append(f"馬爾可夫預測【藍】")

    if b_score > p_score:
        dominant, net_score = 'B', -(b_score - p_score)
        status = f"🔴 莊強 (莊{b_score} vs 閒{p_score})"
    elif p_score > b_score:
        dominant, net_score = 'P', (p_score - b_score)
        status = f"🔵 閒強 (閒{p_score} vs 莊{b_score})"
    else:
        dominant, net_score = 'Neutral', 0
        status = "⚪ 導出訊號持平"

    if mc_status and "樣本不足" not in mc_status:
        details.append(mc_status)

    return {'name': road_name, 'dominant': dominant, 'net_score': net_score, 'status': status, 'details': details}

# ================= 4. 四大核心與 AI 自適應權重學習 =================
def analyze_four_core_roads(history):
    clean_hist = [x for x in history if x in ['B', 'P']]
    total_hands = len(history)

    b_score_big, p_score_big, det_big = analyze_big_road_features(clean_hist)
    big_mc_score, big_mc_fav, big_mc_status = analyze_markov_for_sequence(clean_hist, seq_type="BP")
    
    if big_mc_fav == 'B': b_score_big += 15
    elif big_mc_fav == 'P': p_score_big += 15
    if "樣本不足" not in big_mc_status: det_big.append(big_mc_status)

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

    big_eye_res = analyze_derived_road_core(history, k=1, road_name='2. 大眼仔路 (20%)')
    small_road_res = analyze_derived_road_core(history, k=2, road_name='3. 小路核心 (20%)')
    roach_road_res = analyze_derived_road_core(history, k=3, road_name='4. 曱甴路核心 (20%)')

    roads = {
        'big_road': big_road_res,
        'big_eye': big_eye_res,
        'small_road': small_road_res,
        'roach_road': roach_road_res
    }

    derived_weight = 0.0 if total_hands < 12 else 0.20
    derived_discount = 0.3 if net_big == 0 else 1.0
    effective_derived_weight = derived_weight * derived_discount

    weighted_score = (
        roads['big_road']['net_score'] * 0.40 +
        roads['big_eye']['net_score'] * effective_derived_weight +
        roads['small_road']['net_score'] * effective_derived_weight +
        roads['roach_road']['net_score'] * effective_derived_weight
    )

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

    return roads, weighted_score, is_resonance, confidence_pct

# ================= 5. 主引擎 (AI 學習 + 高自信度保護鎖) =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []

    total_hands = b_count + p_count + t_count
    NATURAL_B, NATURAL_P, NATURAL_T = 45.86, 44.62, 9.52

    four_roads, weighted_road_score, is_resonance, confidence_pct = analyze_four_core_roads(history_list)

    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break

    # 🎯 核心修復：AI 自適應學習與高自信度保護鎖
    is_break_active = False

    # 🌟 風控保護鎖：當可信度 >= 65% (多路共振順勢) 時，嚴禁強行反打！
    if confidence_pct >= 65:
        is_break_active = False
        final_score = weighted_road_score # 順應多路共振 (正打【閒】)
    elif consecutive_losses >= 2 or confidence_pct < 40:
        is_break_active = True
        final_score = -weighted_road_score * 0.6 # 降低反轉幅度，避免過度對抗
    else:
        final_score = weighted_road_score

    # 牌靴宏觀偏態修正 (閒多莊少時給予閒家概率補貼)
    macro_skew = (p_count - b_count) * 0.15

    road_weight_bias = (final_score / 100.0) * 15.0
    l2_b = NATURAL_B - road_weight_bias - macro_skew
    l2_p = NATURAL_P + road_weight_bias + macro_skew

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

    status_msg = f"[AI 自主學習與風控引擎] 自信度: {confidence_pct}% ｜ 牌靴偏態: {macro_skew:+.1f}%"
    return 0.0, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses, status_msg, is_resonance, confidence_pct
