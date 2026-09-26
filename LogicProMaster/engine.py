import random

def init_shoe(num_decks=8):
    """初始化 8 副牌靴 (1-13 面值)"""
    return {val: num_decks * 4 for val in range(1, 14)}

def get_baccarat_value(card):
    return card if card < 10 else 0

def simulate_single_hand(shoe_cards):
    """標準百家樂單局模擬"""
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

# ================= 1. 嚴格五大特徵分析器 =================
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

# ================= 2. 二階馬爾可夫鏈轉移矩陣 (Markov Chain) =================
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
    net_score = (p_prob - b_prob) * 20.0 # 正數偏閒，負數偏莊
    
    pred = "莊" if b_prob > p_prob else ("閒" if p_prob > b_prob else "持平")
    status = f"馬爾可夫轉移: 前【{last_two[0]}{last_two[1]}】➔ 次開【{pred}】(莊{b_next_cnt}/閒{p_next_cnt})"
    return net_score, status

# ================= 3. 單一核心內部決策與「三路共振」加乘 =================
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
    roads = {
        'big_road': evaluate_single_core_road('1. 大路核心', history, k=0),
        'big_eye': evaluate_single_core_road('2. 大眼仔路', history, k=1),
        'small_road': evaluate_single_core_road('3. 小路核心', history, k=2),
        'roach_road': evaluate_single_core_road('4. 曱甴路核心', history, k=3)
    }
    
    # 🎯 下三路「三路共振」爆發加乘
    derived_dominants = [roads['big_eye']['dominant'], roads['small_road']['dominant'], roads['roach_road']['dominant']]
    is_resonance = False
    
    if derived_dominants.count('B') == 3 or derived_dominants.count('P') == 3:
        is_resonance = True
        for key in ['big_eye', 'small_road', 'roach_road']:
            roads[key]['net_score'] *= 1.5 # 觸發 1.5x 共振倍率
            roads[key]['status'] += " (🔥三路共振)"

    return roads, is_resonance

# ================= 4. 五層流水線主引擎 =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []
        
    total_hands = b_count + p_count + t_count
    cards_used = int(total_hands * 4.9)
    total_cards = 8 * 52
    remaining_cards = max(total_cards - cards_used, 52)
    remaining_decks = max(remaining_cards / 52.0, 1.0)
    
    NATURAL_B, NATURAL_P, NATURAL_T = 45.86, 44.62, 9.52

    # 1. 四大路單 (含三路共振)
    four_roads, is_resonance = analyze_four_core_roads(history_list)
    raw_road_score = sum(r['net_score'] for r in four_roads.values())

    # 2. 二階馬爾可夫轉移矩陣
    markov_score, markov_status = analyze_markov_chain(history_list)

    # 3. 衝突度與連爆追蹤
    dominants = [r['dominant'] for r in four_roads.values()]
    is_high_entropy = (dominants.count('B') == 2 and dominants.count('P') == 2)

    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break
            
    is_break_active = False
    is_defense_mode = False

    if consecutive_losses >= 2:
        is_break_active = True
        if is_high_entropy:
            is_defense_mode = True
            final_road_score = 0
        else:
            final_road_score = -(raw_road_score + markov_score) * 0.8
    else:
        final_road_score = raw_road_score + markov_score

    road_weight_bias = (final_road_score / 100.0) * 8.0
    l2_b = NATURAL_B - road_weight_bias
    l2_p = NATURAL_P + road_weight_bias

    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else NATURAL_T
    tie_implicit_bias = (actual_t_ratio - NATURAL_T) * 0.15
    l3_b = l2_b - tie_implicit_bias
    l3_p = l2_p + tie_implicit_bias

    # 4. 殘牌層：100,000 次蒙地卡羅殘牌模擬（含 4 點與 9 點關鍵點數消耗修正）
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

    # 🎯 殘牌關鍵點數（4/9點）動態修正
    # 莊贏多代表 4 點消耗偏多，微調剩餘勝率比重
    key_card_bias = (b_count - p_count) * 0.1
    post_mc_b = l3_b * 0.5 + (mc_b_ratio - key_card_bias) * 0.5
    post_mc_p = l3_p * 0.5 + (mc_p_ratio + key_card_bias) * 0.5

    total_weight = post_mc_b + post_mc_p
    final_b_pct = round((post_mc_b / total_weight) * 100, 1)
    final_p_pct = round((post_mc_p / total_weight) * 100, 1)

    recommend = "觀望 (停注)"
    if not is_defense_mode:
        if final_b_pct >= 52.5:
            recommend = "建議下注【莊】" + (" (⚔️動態反打)" if is_break_active else "")
        elif final_p_pct >= 52.5:
            recommend = "建議下注【閒】" + (" (⚔️動態反打)" if is_break_active else "")

    return avg_tc, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses, markov_status, is_resonance
