# ==============================================================================
# Quantum Baccarat Engine (主次權威重構 + AI 自信度 + 解鎖盲目防禦版)
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

# ================= 1. 嚴格五大特徵獨立分析器 =================
def analyze_five_features_for_sequence(seq):
    n = len(seq)
    b_score, p_score = 0, 0
    details = []
    if n < 3: return 0, 0, ["數據不足"]

    # 1. 單跳
    if n >= 3 and seq[-1] != seq[-2] and seq[-2] != seq[-3]:
        target = 'B' if seq[-1] == 'P' else 'P'
        if target == 'B': b_score += 15
        else: p_score += 15
        details.append(f"單跳強向【{'莊' if target=='B' else '閒'}】")

    # 2. 雙跳
    if n >= 4 and seq[-1] == seq[-2] and seq[-3] == seq[-4] and seq[-1] != seq[-3]:
        target = 'B' if seq[-1] == 'P' else 'P'
        if target == 'B': b_score += 20
        else: p_score += 20
        details.append(f"雙跳強向【{'莊' if target=='B' else '閒'}】")

    # 3. 長龍
    streak = 1
    for i in range(n-2, -1, -1):
        if seq[i] == seq[-1]: streak += 1
        else: break
    if streak >= 3:
        target = seq[-1]
        s = streak * 8
        if target == 'B': b_score += s
        else: p_score += s
        details.append(f"長龍連{streak}【{'莊' if target=='B' else '閒'}】")

    # 4. 房廳結構
    if n >= 6 and seq[-3:] == seq[-6:-3] and len(set(seq[-3:])) == 2:
        predict_next = seq[-3]
        if predict_next == 'B': b_score += 16
        else: p_score += 16
        details.append(f"房廳週期【{'莊' if predict_next=='B' else '閒'}】")

    # 5. 逢跳連
    if n >= 5:
        jumps_then_streak = True
        for i in range(2, n-1):
            if seq[i] != seq[i-1] and seq[i-1] == seq[i-2]:
                if seq[i+1] != seq[i]:
                    jumps_then_streak = False
                    break
        if jumps_then_streak and seq[-1] != seq[-2]:
            next_target = seq[-1]
            if next_target == 'B': b_score += 18
            else: p_score += 18
            details.append(f"逢跳連【{'莊' if next_target=='B' else '閒'}】")

    return b_score, p_score, details

# ================= 2. 二階馬爾可夫轉移矩陣 =================
def analyze_markov_chain(history):
    clean_hist = [x for x in history if x in ['B', 'P']]
    n = len(clean_hist)
    if n < 4: return 0, "馬爾可夫數據不足"
    
    last_two = (clean_hist[-2], clean_hist[-1])
    b_next_cnt, p_next_cnt = 0, 0
    
    for i in range(n - 2):
        if (clean_hist[i], clean_hist[i+1]) == last_two:
            next_val = clean_hist[i+2]
            if next_val == 'B': b_next_cnt += 1
            elif next_val == 'P': p_next_cnt += 1
            
    tot = b_next_cnt + p_next_cnt
    if tot == 0: return 0, "馬爾可夫無歷史比對"
    
    b_prob = b_next_cnt / tot
    p_prob = p_next_cnt / tot
    net_score = (p_prob - b_prob) * 25.0
    
    pred = "莊" if b_prob > p_prob else ("閒" if p_prob > b_prob else "持平")
    status = f"馬爾可夫轉移: 前【{last_two[0]}{last_two[1]}】➔ 次開【{pred}】(莊{b_next_cnt}/閒{p_next_cnt})"
    return net_score, status

# ================= 3. 單一核心內部決策 =================
def evaluate_single_core_road(road_name, history, k=0):
    clean_hist = [x for x in history if x in ['B', 'P']]
    if k == 0:
        b_score, p_score, details = analyze_five_features_for_sequence(clean_hist)
    else:
        cols_b = build_logical_columns(history + ['B'])
        cols_p = build_logical_columns(history + ['P'])
        b_score, _, det_b = analyze_five_features_for_sequence(['B' if x=='Red' else 'P' for x in get_derived_road(cols_b, k)])
        p_score, _, det_p = analyze_five_features_for_sequence(['B' if x=='Red' else 'P' for x in get_derived_road(cols_p, k)])
        details = [f"開莊特徵: {len(det_b)}", f"開閒特徵: {len(det_p)}"]

    if b_score > p_score:
        dominant, net_score = 'B', -(b_score - p_score)
        status = f"🔴 莊強 (莊{b_score} vs 閒{p_score})"
    elif p_score > b_score:
        dominant, net_score = 'P', (p_score - b_score)
        status = f"🔵 閒強 (閒{p_score} vs 莊{b_score})"
    else:
        dominant, net_score = 'Neutral', 0
        status = "⚪ 訊號持平"

    return {'name': road_name, 'dominant': dominant, 'b_score': b_score, 'p_score': p_score, 'net_score': net_score, 'status': status, 'details': details}

# ================= 4. 主次權威加權與自信度矩陣 =================
def analyze_four_core_roads(history):
    roads = {
        'big_road': evaluate_single_core_road('1. 大路核心 (主軸40%)', history, k=0),
        'big_eye': evaluate_single_core_road('2. 大眼仔路 (20%)', history, k=1),
        'small_road': evaluate_single_core_road('3. 小路核心 (20%)', history, k=2),
        'roach_road': evaluate_single_core_road('4. 曱甴路核心 (20%)', history, k=3)
    }
    
    # 🎯 權威加權計算 (大路 40%, 下三路各 20%)
    weighted_score = (
        roads['big_road']['net_score'] * 0.40 +
        roads['big_eye']['net_score'] * 0.20 +
        roads['small_road']['net_score'] * 0.20 +
        roads['roach_road']['net_score'] * 0.20
    )
    
    # 三路共振爆發檢查
    derived_dominants = [roads['big_eye']['dominant'], roads['small_road']['dominant'], roads['roach_road']['dominant']]
    is_resonance = False
    if derived_dominants.count('B') == 3 or derived_dominants.count('P') == 3:
        is_resonance = True
        weighted_score *= 1.4 # 共振時加強整體權重
        for key in ['big_eye', 'small_road', 'roach_road']:
            roads[key]['status'] += " (🔥共振)"

    # 計算 AI 自信度指數 (Confidence Index)
    valid_dominants = [r['dominant'] for r in roads.values() if r['dominant'] != 'Neutral']
    if valid_dominants:
        most_common = max(set(valid_dominants), key=valid_dominants.count)
        confidence_pct = round((valid_dominants.count(most_common) / len(valid_dominants)) * 100)
    else:
        confidence_pct = 50

    return roads, weighted_score, is_resonance, confidence_pct

# ================= 5. 純統計與馬爾可夫主引擎 =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []
        
    total_hands = b_count + p_count + t_count
    NATURAL_B, NATURAL_P, NATURAL_T = 45.86, 44.62, 9.52

    # 四大核心（主次權威加權）
    four_roads, weighted_road_score, is_resonance, confidence_pct = analyze_four_core_roads(history_list)

    # 二階馬爾可夫轉移矩陣
    markov_score, markov_status = analyze_markov_chain(history_list)

    # 追蹤歷史連爆局數
    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break
            
    is_break_active = False
    is_defense_mode = False

    # 🛡️ 解鎖盲目防禦：只有當「自信度指數 < 30% 且 連爆 >= 3 局」時才強制進入防禦觀望
    if consecutive_losses >= 3 and confidence_pct < 30:
        is_defense_mode = True
        final_score = 0
    elif consecutive_losses >= 2:
        is_break_active = True
        final_score = -(weighted_road_score + markov_score * 0.5) * 0.75 # 平滑動態修正，不再盲目歸零
    else:
        final_score = weighted_road_score + markov_score * 0.5

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

    # 合理化進場決策門檻 (51.2%)
    recommend = "觀望 (停注)"
    if not is_defense_mode:
        if final_b_pct >= 51.2:
            recommend = "建議下注【莊】" + (" (⚔️動態微調)" if is_break_active else "")
        elif final_p_pct >= 51.2:
            recommend = "建議下注【閒】" + (" (⚔️動態微調)" if is_break_active else "")

    return 0.0, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses, markov_status, is_resonance, confidence_pct
