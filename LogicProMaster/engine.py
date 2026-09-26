import random

def init_shoe(num_decks=8):
    return {val: num_decks * 4 for val in range(1, 14)}

def get_baccarat_value(card):
    return card if card < 10 else 0

def simulate_single_hand(shoe_cards):
    if len(shoe_cards) < 6: return None
    drawn = random.sample(shoe_cards, 6)
    c_p1, c_b1, c_p2, c_b2, c_p3, c_b3 = drawn
    p_score = (get_baccarat_value(c_p1) + get_baccarat_value(c_p2)) % 10
    b_score = (get_baccarat_value(c_b1) + get_baccarat_value(c_b2)) % 10
    
    p_third = None
    if p_score < 6 and b_score < 8:
        p_third = get_baccarat_value(c_p3)
        p_score = (p_score + p_third) % 10
        
    if b_score < 8:
        draw_b = False
        if p_third is None:
            if b_score < 6: draw_b = True
        else:
            if b_score <= 2: draw_b = True
            elif b_score == 3 and p_third != 8: draw_b = True
            elif b_score == 4 and p_third in [2,3,4,5,6,7]: draw_b = True
            elif b_score == 5 and p_third in [4,5,6,7]: draw_b = True
            elif b_score == 6 and p_third in [6,7]: draw_b = True
        if draw_b:
            b_score = (b_score + get_baccarat_value(c_b3)) % 10

    if b_score > p_score: return 'B'
    elif p_score > b_score: return 'P'
    else: return 'T'

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

def analyze_five_features_for_sequence(seq):
    n = len(seq)
    b_score, p_score = 0, 0
    details = []
    if n < 3: return 0, 0, ["數據不足"]

    # 1.單跳 2.雙跳 3.長龍 4.房廳 5.逢跳連
    if n >= 3 and seq[-1] != seq[-2] and seq[-2] != seq[-3]:
        target = 'B' if seq[-1] == 'P' else 'P'
        if target == 'B': b_score += 15
        else: p_score += 15
        details.append(f"單跳強向【{'莊' if target=='B' else '閒'}】")

    if n >= 4 and seq[-1] == seq[-2] and seq[-3] == seq[-4] and seq[-1] != seq[-3]:
        target = 'B' if seq[-1] == 'P' else 'P'
        if target == 'B': b_score += 20
        else: p_score += 20
        details.append(f"雙跳強向【{'莊' if target=='B' else '閒'}】")

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

    if n >= 6 and seq[-3:] == seq[-6:-3] and len(set(seq[-3:])) == 2:
        predict_next = seq[-3]
        if predict_next == 'B': b_score += 16
        else: p_score += 16
        details.append(f"房廳週期【{'莊' if predict_next=='B' else '閒'}】")

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

def analyze_four_core_roads(history):
    return {
        'big_road': evaluate_single_core_road('1. 大路核心', history, k=0),
        'big_eye': evaluate_single_core_road('2. 大眼仔路', history, k=1),
        'small_road': evaluate_single_core_road('3. 小路核心', history, k=2),
        'roach_road': evaluate_single_core_road('4. 曱甴路核心', history, k=3)
    }

def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []
        
    total_hands = b_count + p_count + t_count
    cards_used = int(total_hands * 4.9)
    total_cards = 8 * 52
    remaining_cards = max(total_cards - cards_used, 52)
    remaining_decks = max(remaining_cards / 52.0, 1.0)
    
    NATURAL_B, NATURAL_P, NATURAL_T = 45.86, 44.62, 9.52

    # 四大路單分析
    four_roads = analyze_four_core_roads(history_list)
    raw_road_score = sum(r['net_score'] for r in four_roads.values())
    
    # 計算路單訊號衝突度/亂度 (Chaos Dispersion)
    dominants = [r['dominant'] for r in four_roads.values()]
    b_dominants = dominants.count('B')
    p_dominants = dominants.count('P')
    is_high_entropy = (b_dominants == 2 and p_dominants == 2) # 四大路單 2莊2閒 極度混亂

    # 連爆追蹤
    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break
            
    is_break_active = False
    is_defense_mode = False

    # 🎯 動態自適應破路邏輯
    if consecutive_losses >= 2:
        is_break_active = True
        if is_high_entropy:
            # 情況 A：盤口亂且連爆 -> 啟動高熵避險鎖 (權重強制歸零，強制觀望)
            is_defense_mode = True
            final_road_score = 0
        else:
            # 情況 B：盤口有明確指向但連爆 -> 進行平滑軟性反轉 (-0.8x 避免極端雙向抽擊)
            final_road_score = -raw_road_score * 0.8
    else:
        final_road_score = raw_road_score

    road_weight_bias = (final_road_score / 100.0) * 8.0
    l2_b = NATURAL_B - road_weight_bias
    l2_p = NATURAL_P + road_weight_bias

    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else NATURAL_T
    tie_implicit_bias = (actual_t_ratio - NATURAL_T) * 0.15
    l3_b = l2_b - tie_implicit_bias
    l3_p = l2_p + tie_implicit_bias

    # 100,000 次蒙地卡羅殘牌模擬
    raw_rc = (p_count - b_count) * 0.5
    avg_tc = raw_rc / remaining_decks

    base_shoe = init_shoe(8)
    shoe_list = []
    for card, count in base_shoe.items():
        shoe_list.extend([card] * count)
        
    random.shuffle(shoe_list)
    if cards_used > 0 and len(shoe_list) > cards_used:
        shoe_list = shoe_list[cards_used:]

    results = {'B': 0, 'P': 0, 'T': 0}
    if len(shoe_list) >= 6:
        for _ in range(sim_count):
            res = simulate_single_hand(shoe_list)
            if res: results[res] += 1

    total_sims = max(1, sum(results.values()))
    mc_b_ratio = (results['B'] / total_sims) * 100
    mc_p_ratio = (results['P'] / total_sims) * 100

    post_mc_b = l3_b * 0.5 + mc_b_ratio * 0.5
    post_mc_p = l3_p * 0.5 + mc_p_ratio * 0.5

    total_weight = post_mc_b + post_mc_p
    final_b_pct = round((post_mc_b / total_weight) * 100, 1)
    final_p_pct = round((post_mc_p / total_weight) * 100, 1)

    recommend = "觀望 (停注)"
    if not is_defense_mode:
        if final_b_pct >= 52.5:
            recommend = "建議下注【莊】" + (" (⚔️動態反打)" if is_break_active else "")
        elif final_p_pct >= 52.5:
            recommend = "建議下注【閒】" + (" (⚔️動態反打)" if is_break_active else "")

    return avg_tc, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses
