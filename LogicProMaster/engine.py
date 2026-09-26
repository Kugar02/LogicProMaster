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

# --- 四大路單構建輔助函數 ---
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

def analyze_four_core_roads(history):
    """
    將大路與下三路分拆，構成 4 大核心分析模組
    回傳四大路單各自的傾向分 (正數偏閒，負數偏莊)
    """
    clean_hist = [x for x in history if x in ['B', 'P']]
    n = len(clean_hist)
    
    road_scores = {
        'big_road': {'name': '1. 大路核心 (Big Road)', 'score': 0, 'status': '觀望'},
        'big_eye': {'name': '2. 大眼仔路 (Big Eye)', 'score': 0, 'status': '觀望'},
        'small_road': {'name': '3. 小路核心 (Small Road)', 'score': 0, 'status': '觀望'},
        'roach_road': {'name': '4. 曱甴路核心 (Roach Road)', 'score': 0, 'status': '觀望'}
    }
    
    if n < 3:
        return road_scores

    # 1. 大路分析 (長龍、單跳、雙跳)
    streak = 1
    for i in range(n-2, -1, -1):
        if clean_hist[i] == clean_hist[-1]: streak += 1
        else: break
        
    if streak >= 3:
        target = clean_hist[-1]
        s = (streak * 8) if target == 'P' else -(streak * 8)
        road_scores['big_road']['score'] = s
        road_scores['big_road']['status'] = f"{'閒' if target=='P' else '莊'}龍趨勢 (連開 {streak} 局)"
    elif clean_hist[-1] != clean_hist[-2]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        s = 12 if target == 'P' else -12
        road_scores['big_road']['score'] = s
        road_scores['big_road']['status'] = "單跳走勢中"

    # 2-4. 下三路獨立分析 (大眼仔、小路、曱甴路)
    logical_cols = build_logical_columns(history)
    
    for k, key_name, road_title in [(1, 'big_eye', '大眼仔路'), (2, 'small_road', '小路'), (3, 'roach_road', '曱甴路')]:
        derived = get_derived_road(logical_cols, k)
        if derived:
            recent = derived[-3:]
            red_cnt = recent.count('Red')
            blue_cnt = recent.count('Blue')
            # 紅筆多代表整齊規律，藍筆多代表雜亂
            if red_cnt > blue_cnt:
                road_scores[key_name]['score'] = 10 if clean_hist[-1] == 'P' else -10
                road_scores[key_name]['status'] = f"{road_title}呈現整齊紅筆，順勢看好"
            elif blue_cnt > red_cnt:
                road_scores[key_name]['score'] = -10 if clean_hist[-1] == 'P' else 10
                road_scores[key_name]['status'] = f"{road_title}呈現藍筆跳路，看好轉項"

    return road_scores

def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    """
    100,000 次蒙地卡羅 + 4大路單分拆 + 天生勝率底座 + 和局隱性影響 + 智能破路整合
    """
    if history_list is None: history_list = []
    if ai_targets is None: ai_targets = []
        
    total_hands = b_count + p_count + t_count
    cards_used = int(total_hands * 4.9)
    total_cards = 8 * 52
    remaining_cards = max(total_cards - cards_used, 52)
    remaining_decks = max(remaining_cards / 52.0, 1.0)
    
    # 1. 天生勝率概念基礎 (Natural Base Probabilities)
    NATURAL_B = 45.86
    NATURAL_P = 44.62
    NATURAL_T = 9.52

    # 2. 和局隱性影響機制 (Tie Implicit Impact)
    # 和局雖不影響大路，但消耗殘牌且拉長盤局，若和局率偏離 9.52%，調整波動修正分
    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else NATURAL_T
    tie_implicit_bias = (actual_t_ratio - NATURAL_T) * 0.15 # 和局影響微調權重

    # 3. 執行 100,000 次蒙地卡羅殘牌矩陣模擬
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
    mc_b_prob = (results['B'] / total_sims) * 100
    mc_p_prob = (results['P'] / total_sims) * 100

    # 4. 拆解 4 大核心路單分析
    four_roads = analyze_four_core_roads(history_list)
    raw_road_score = sum(r['score'] for r in four_roads.values())

    # 5. 整合智能破路 / 反打策略 (自動檢測連爆連敗)
    consecutive_losses = 0
    for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
        if tgt and tgt.get('target') and actual != 'T':
            if tgt['target'] != actual: consecutive_losses += 1
            else: break
            
    is_break_active = False
    if consecutive_losses >= 2:
        is_break_active = True
        final_road_score = -raw_road_score * 1.3 # 強制反轉 4 大路單權重 1.3 倍
    else:
        final_road_score = raw_road_score

    # 6. 整合最終權重百分比對比 (天生勝率 + 蒙地卡羅 + 4大路單 + 和局隱性)
    # 將所有動態因子折算為莊閒權重
    road_weight_bias = (final_road_score / 100.0) * 8.0 # 最大 ±8% 影響
    
    # 計算複合權重比值
    composite_b = NATURAL_B + (mc_b_prob - NATURAL_B) * 0.4 - road_weight_bias - tie_implicit_bias
    composite_p = NATURAL_P + (mc_p_prob - NATURAL_P) * 0.4 + road_weight_bias + tie_implicit_bias

    # 歸一化為 100% 莊閒對比百分比 (不含和局)
    total_bp = composite_b + composite_p
    final_b_pct = round((composite_b / total_bp) * 100, 1)
    final_p_pct = round((composite_p / total_bp) * 100, 1)

    # 輸出最終建議
    recommend = "觀望 (停注)"
    if final_b_pct >= 52.5:
        recommend = "建議下注【莊】" + (" (⚔️智能破路反打)" if is_break_active else "")
    elif final_p_pct >= 52.5:
        recommend = "建議下注【閒】" + (" (⚔️智能破路反打)" if is_break_active else "")

    return avg_tc, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses
