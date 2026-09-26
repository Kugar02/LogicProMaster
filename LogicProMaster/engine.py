import random

def init_shoe(num_decks=8):
    """初始化 8 副牌靴 (1-13 面值)"""
    return {val: num_decks * 4 for val in range(1, 14)}

def get_baccarat_value(card):
    return card if card < 10 else 0

def simulate_single_hand(shoe_cards):
    """標準百家樂單局模擬"""
    if len(shoe_cards) < 6:
        return None
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

# ================= 1. 嚴格六大特徵分析器 =================
def analyze_six_features_for_sequence(seq):
    """
    對指定序列嚴格執行六大特徵檢測：
    1.單跳 2.雙跳 3.長龍 4.房廳 5.逢跳連 6.九宮格
    回傳：莊訊號得分, 閒訊號得分, 特徵診斷清單
    """
    n = len(seq)
    b_score, p_score = 0, 0
    details = []

    if n < 3:
        return 0, 0, ["數據不充分 (需至少3局)"]

    # 特徵 1: 單跳 (B-P-B-P...)
    if n >= 3 and seq[-1] != seq[-2] and seq[-2] != seq[-3]:
        target = 'B' if seq[-1] == 'P' else 'P'
        strength = 15
        if target == 'B': b_score += strength
        else: p_score += strength
        details.append(f"單跳特徵: 強向【{'莊' if target=='B' else '閒'}】(+{strength})")

    # 特徵 2: 雙跳 (BB-PP-BB...)
    if n >= 4 and seq[-1] == seq[-2] and seq[-3] == seq[-4] and seq[-1] != seq[-3]:
        target = 'B' if seq[-1] == 'P' else 'P'
        strength = 20
        if target == 'B': b_score += strength
        else: p_score += strength
        details.append(f"雙跳特徵: 強向【{'莊' if target=='B' else '閒'}】(+{strength})")

    # 特徵 3: 長龍 (BBB... 或 PPP...)
    streak = 1
    for i in range(n-2, -1, -1):
        if seq[i] == seq[-1]: streak += 1
        else: break
    if streak >= 3:
        target = seq[-1]
        strength = streak * 8
        if target == 'B': b_score += strength
        else: p_score += strength
        details.append(f"長龍特徵(連{streak}): 順勢【{'莊' if target=='B' else '閒'}】(+{strength})")

    # 特徵 4: 房廳結構 (1房2廳 BPP BPP 或 2房1廳 BBP BBP)
    if n >= 6:
        block3 = seq[-3:]
        prev_block3 = seq[-6:-3]
        if block3 == prev_block3 and len(set(block3)) == 2:
            predict_next = block3[0]
            strength = 16
            if predict_next == 'B': b_score += strength
            else: p_score += strength
            details.append(f"房廳週期: 看好【{'莊' if predict_next=='B' else '閒'}】(+{strength})")

    # 特徵 5: 逢跳連 (跳後必連)
    if n >= 5:
        jumps_then_streak = True
        for i in range(2, n-1):
            if seq[i] != seq[i-1] and seq[i-1] == seq[i-2]:
                if seq[i+1] != seq[i]:
                    jumps_then_streak = False
                    break
        if jumps_then_streak and seq[-1] != seq[-2]:
            next_target = seq[-1]
            strength = 18
            if next_target == 'B': b_score += strength
            else: p_score += strength
            details.append(f"逢跳連特徵: 跟連【{'莊' if next_target=='B' else '閒'}】(+{strength})")

    # 特徵 6: 九宮格矩陣 (近 9 局空間平衡)
    if n >= 9:
        grid9 = seq[-9:]
        b_cnt = grid9.count('B')
        p_cnt = grid9.count('P')
        if b_cnt > p_cnt + 2:
            strength = 12
            p_score += strength
            details.append(f"九宮格修正: 看好【閒】(+{strength})")
        elif p_cnt > b_cnt + 2:
            strength = 12
            b_score += strength
            details.append(f"九宮格修正: 看好【莊】(+{strength})")

    return b_score, p_score, details

# ================= 2. 單一核心內部強弱決策 =================
def evaluate_single_core_road(road_name, history, k=0):
    """
    針對每個核心路單，跑滿六大特徵，比較莊 vs 閒強弱，
    並將同一個方向較強者作為該核心的最終結果。
    """
    clean_hist = [x for x in history if x in ['B', 'P']]
    
    if k == 0:
        # 大路直接進行六大特徵分析
        b_score, p_score, details = analyze_six_features_for_sequence(clean_hist)
    else:
        # 下三路：利用問路模擬下一局開莊與開閒對下三路紅/藍品質的六大特徵比對
        cols_b = build_logical_columns(history + ['B'])
        derived_b = get_derived_road(cols_b, k)
        
        cols_p = build_logical_columns(history + ['P'])
        derived_p = get_derived_road(cols_p, k)
        
        # 評估導出的紅筆 (整齊) 與藍筆 (跳路) 特徵
        b_score, _, det_b = analyze_six_features_for_sequence(['B' if x=='Red' else 'P' for x in derived_b])
        p_score, _, det_p = analyze_six_features_for_sequence(['B' if x=='Red' else 'P' for x in derived_p])
        details = [f"開莊導出特徵數: {len(det_b)}", f"開閒導出特徵數: {len(det_p)}"]

    # 精準判斷哪一個特徵方向訊號較強，作為該核心最終結論
    if b_score > p_score:
        dominant = 'B'
        net_score = -(b_score - p_score) # 負數表示偏莊
        status = f"🔴 莊訊號較強 (莊 {b_score}分 vs 閒 {p_score}分)"
    elif p_score > b_score:
        dominant = 'P'
        net_score = (p_score - b_score) # 正數表示偏閒
        status = f"🔵 閒訊號較強 (閒 {p_score}分 vs 莊 {b_score}分)"
    else:
        dominant = 'Neutral'
        net_score = 0
        status = "⚪ 莊閒訊號持平 (0 vs 0)"

    return {
        'name': road_name,
        'dominant': dominant,
        'b_score': b_score,
        'p_score': p_score,
        'net_score': net_score,
        'status': status,
        'details': details
    }

def analyze_four_core_roads(history):
    return {
        'big_road': evaluate_single_core_road('1. 大路核心 (Big Road)', history, k=0),
        'big_eye': evaluate_single_core_road('2. 大眼仔路核心 (Big Eye)', history, k=1),
        'small_road': evaluate_single_core_road('3. 小路核心 (Small Road)', history, k=2),
        'roach_road': evaluate_single_core_road('4. 曱甴路核心 (Roach Road)', history, k=3)
    }

# ================= 3. 五層流水線整合主引擎 =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    """
    五層整合流水線：
    [底座層] ➔ [路型層 (含破路)] ➔ [隱性層] ➔ [殘牌蒙地卡羅層 (100K)] ➔ [最終歸一化]
    """
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []
        
    total_hands = b_count + p_count + t_count
    cards_used = int(total_hands * 4.9)
    total_cards = 8 * 52
    remaining_cards = max(total_cards - cards_used, 52)
    remaining_decks = max(remaining_cards / 52.0, 1.0)
    
    # --- 第 1 層：底座層 (Base Layer) ---
    NATURAL_B = 45.86
    NATURAL_P = 44.62
    NATURAL_T = 9.52

    # --- 第 2 層：路型層 (Road Pattern Layer - 4大核心六特徵比對) ---
    four_roads = analyze_four_core_roads(history_list)
    raw_road_score = sum(r['net_score'] for r in four_roads.values())

    # 智能破路 / 反打機制 (連爆 2 局自動觸發 Signal Inversion)
    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break
            
    is_break_active = False
    if consecutive_losses >= 2:
        is_break_active = True
        final_road_score = -raw_road_score * 1.3 # 強制反轉四大路單權重 1.3 倍
    else:
        final_road_score = raw_road_score

    road_weight_bias = (final_road_score / 100.0) * 8.0
    l2_b = NATURAL_B - road_weight_bias
    l2_p = NATURAL_P + road_weight_bias

    # --- 第 3 層：隱性層 (Implicit Tie Layer) ---
    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else NATURAL_T
    tie_implicit_bias = (actual_t_ratio - NATURAL_T) * 0.15 # 和局偏離修正
    
    l3_b = l2_b - tie_implicit_bias
    l3_p = l2_p + tie_implicit_bias

    # --- 第 4 層：殘牌層 (Remaining Shoe Monte Carlo Layer - 100,000 局) ---
    # 結合【底座+路型+隱性】前三層整合資料 + 全局已開出殘牌數據進行 100,000 局模擬
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

    # 殘牌模擬結果與前三層整合數據之融合
    post_mc_b = l3_b * 0.5 + mc_b_ratio * 0.5
    post_mc_p = l3_p * 0.5 + mc_p_ratio * 0.5

    # --- 第 5 層：最終歸一化 (Normalization) ---
    total_weight = post_mc_b + post_mc_p
    final_b_pct = round((post_mc_b / total_weight) * 100, 1)
    final_p_pct = round((post_mc_p / total_weight) * 100, 1)

    recommend = "觀望 (停注)"
    if final_b_pct >= 52.5:
        recommend = "建議下注【莊】" + (" (⚔️智能破路反打)" if is_break_active else "")
    elif final_p_pct >= 52.5:
        recommend = "建議下注【閒】" + (" (⚔️智能破路反打)" if is_break_active else "")

    return avg_tc, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses
