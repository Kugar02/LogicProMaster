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

def analyze_patterns(history):
    """
    六大路型邏輯分析器
    回傳莊閒權重分 (正數偏閒，負數偏莊，0為中立) 與型態診斷報告
    """
    clean_hist = [x for x in history if x in ['B', 'P']]
    n = len(clean_hist)
    
    patterns = {
        'single_jump': {'name': '單跳 (B-P-B-P)', 'score': 0, 'status': '未觸發'},
        'double_jump': {'name': '雙跳 (BB-PP)', 'score': 0, 'status': '未觸發'},
        'dragon': {'name': '長龍趨勢', 'score': 0, 'status': '未觸發'},
        'room_hall': {'name': '房廳結構 (一房兩廳/兩房一廳)', 'score': 0, 'status': '未觸發'},
        'jump_and_streak': {'name': '逢跳連 (跳後必連)', 'score': 0, 'status': '未觸發'},
        'nine_grid': {'name': '九宮格矩陣對稱性', 'score': 0, 'status': '未觸發'}
    }
    
    if n < 3:
        return 0, patterns

    # 1. 單跳偵測 (交替趨勢)
    if n >= 3:
        if clean_hist[-1] != clean_hist[-2] and clean_hist[-2] != clean_hist[-3]:
            next_target = 'B' if clean_hist[-1] == 'P' else 'P'
            score = 15 if next_target == 'P' else -15
            patterns['single_jump']['score'] = score
            patterns['single_jump']['status'] = f"已連跳 {3} 局，預估下局開【{'閒' if next_target=='P' else '莊'}】"

    # 2. 雙跳偵測 (BB-PP-BB-PP)
    if n >= 4:
        if clean_hist[-1] == clean_hist[-2] and clean_hist[-3] == clean_hist[-4] and clean_hist[-1] != clean_hist[-3]:
            next_target = 'B' if clean_hist[-1] == 'P' else 'P'
            score = 20 if next_target == 'P' else -20
            patterns['double_jump']['score'] = score
            patterns['double_jump']['status'] = f"雙跳型態成型，預估轉項開【{'閒' if next_target=='P' else '莊'}】"

    # 3. 長龍偵測 (連開 3+ 局)
    streak = 1
    for i in range(n-2, -1, -1):
        if clean_hist[i] == clean_hist[-1]: streak += 1
        else: break
    if streak >= 3:
        next_target = clean_hist[-1]
        score = (streak * 10) if next_target == 'P' else -(streak * 10)
        patterns['dragon']['score'] = score
        patterns['dragon']['status'] = f"🔥 {'莊' if next_target=='B' else '閒'}龍連開 {streak} 局，順龍看好【{'閒' if next_target=='P' else '莊'}】"

    # 4. 房廳結構 (1房2廳 BPP BPP 或 2房1房 BBP BBP)
    if n >= 6:
        block3 = clean_hist[-3:]
        prev_block3 = clean_hist[-6:-3]
        if block3 == prev_block3 and len(set(block3)) == 2:
            # 判斷循環下一位的預期
            predict_next = block3[0] # 假設 3 局一循環
            score = 15 if predict_next == 'P' else -15
            patterns['room_hall']['score'] = score
            patterns['room_hall']['status'] = f"觸發週期房廳結構，看好【{'閒' if predict_next=='P' else '莊'}】"

    # 5. 逢跳連 (跳一次後下一局必定連開)
    if n >= 5:
        jumps_then_streak = True
        for i in range(2, n-1):
            if clean_hist[i] != clean_hist[i-1] and clean_hist[i-1] == clean_hist[i-2]:
                if clean_hist[i+1] != clean_hist[i]:
                    jumps_then_streak = False
                    break
        if jumps_then_streak and clean_hist[-1] != clean_hist[-2]:
            next_target = clean_hist[-1] # 逢跳後預期跟連
            score = 18 if next_target == 'P' else -18
            patterns['jump_and_streak']['score'] = score
            patterns['jump_and_streak']['status'] = f"符合逢跳必連規律，看好【{'閒' if next_target=='P' else '莊'}】連開"

    # 6. 九宮格矩陣分析 (近 9 局 3x3 空間分佈)
    if n >= 9:
        grid9 = clean_hist[-9:]
        b_grid_count = grid9.count('B')
        p_grid_count = grid9.count('P')
        # 對角線與欄位對稱比對
        if b_grid_count > p_grid_count + 2:
            patterns['nine_grid']['score'] = 12 # 均值回歸偏閒
            patterns['nine_grid']['status'] = f"九宮格莊多({b_grid_count}/9)，矩陣修正看好【閒】"
        elif p_grid_count > b_grid_count + 2:
            patterns['nine_grid']['score'] = -12 # 均值回歸偏莊
            patterns['nine_grid']['status'] = f"九宮格閒多({p_grid_count}/9)，矩陣修正看好【莊】"

    total_pattern_score = sum(p['score'] for p in patterns.values())
    return total_pattern_score, patterns

def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None):
    """
    100,000 次蒙地卡羅殘牌矩陣 + 六大路型動態加權引擎
    """
    if history_list is None:
        history_list = []
        
    total_hands = b_count + p_count + t_count
    cards_used = int(total_hands * 4.9)
    total_cards = 8 * 52
    remaining_cards = max(total_cards - cards_used, 52)
    remaining_decks = max(remaining_cards / 52.0, 1.0)
    
    raw_rc = (p_count - b_count) * 0.5
    avg_tc = raw_rc / remaining_decks

    # 生成剩餘牌靴
    base_shoe = init_shoe(8)
    shoe_list = []
    for card, count in base_shoe.items():
        shoe_list.extend([card] * count)
        
    random.shuffle(shoe_list)
    if cards_used > 0 and len(shoe_list) > cards_used:
        shoe_list = shoe_list[cards_used:]

    if len(shoe_list) < 6:
        return None, 0, 0, 0, "剩餘牌數不足", 0, 0, {}

    # 1. 執行 100,000 次蒙地卡羅殘牌模擬
    results = {'B': 0, 'P': 0, 'T': 0}
    for _ in range(sim_count):
        res = simulate_single_hand(shoe_list)
        if res: results[res] += 1

    total_sims = sum(results.values())
    mc_b_prob = (results['B'] / total_sims) * 100
    mc_p_prob = (results['P'] / total_sims) * 100
    mc_t_prob = (results['T'] / total_sims) * 100

    # 2. 計算路形特徵權重
    pattern_score, patterns_detail = analyze_patterns(history_list)

    # 3. 綜合加權公式：60% 殘牌蒙地卡羅概率 + 40% 路型形態修正
    # pattern_score 正值偏閒，負值偏莊
    weight_bias = (pattern_score / 100.0) * 5.0 # 最大 ±5% 修正幅度
    
    final_p_prob = max(0.0, min(100.0, mc_p_prob + weight_bias))
    final_b_prob = max(0.0, min(100.0, mc_b_prob - weight_bias))

    # 決策門檻 (考慮 5% 莊水)
    ev_b = (final_b_prob / 100 * 0.95) - (final_p_prob / 100)
    ev_p = (final_p_prob / 100 * 1.0) - (final_b_prob / 100)

    recommend = "觀望 (停注)"
    if ev_b > 0 and ev_b > ev_p and final_b_prob > 48.5:
        recommend = "建議下注【莊】"
    elif ev_p > 0 and ev_p > ev_b and final_p_prob > 50.0:
        recommend = "建議下注【閒】"

    return avg_tc, final_b_prob, final_p_prob, mc_t_prob, recommend, pattern_score, patterns_detail
