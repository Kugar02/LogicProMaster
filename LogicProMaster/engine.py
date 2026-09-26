import random

def init_shoe(num_decks=8):
    return {val: num_decks * 4 for val in range(1, 14)}

def get_baccarat_value(card):
    return card if card < 10 else 0

def simulate_single_hand(shoe_cards):
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

    if b_score > p_score: return 'Banker'
    elif p_score > b_score: return 'Player'
    else: return 'Tie'

def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=20000):
    total_hands = b_count + p_count + t_count
    
    # 假設平均每局消耗 4.9 張牌
    cards_used = int(total_hands * 4.9)
    total_cards = 8 * 52
    remaining_cards = max(total_cards - cards_used, 52)
    remaining_decks = max(remaining_cards / 52.0, 1.0)
    
    # 依局數推算估算 TC (大於 0 偏向閒，小於 0 偏向莊)
    raw_rc = (p_count - b_count) * 0.5
    avg_tc = raw_rc / remaining_decks

    # 生成預測剩餘牌堆
    base_shoe = init_shoe(8)
    shoe_list = []
    for card, count in base_shoe.items():
        shoe_list.extend([card] * count)
        
    random.shuffle(shoe_list)
    if cards_used > 0 and len(shoe_list) > cards_used:
        shoe_list = shoe_list[cards_used:]

    if len(shoe_list) < 6:
        return None, 0, 0, 0, "剩餘牌數不足，請洗牌重置", 0, 0

    # 蒙地卡羅模擬
    results = {'Banker': 0, 'Player': 0, 'Tie': 0}
    for _ in range(sim_count):
        res = simulate_single_hand(shoe_list)
        if res: results[res] += 1

    total_sims = sum(results.values())
    b_prob = (results['Banker'] / total_sims) * 100
    p_prob = (results['Player'] / total_sims) * 100
    t_prob = (results['Tie'] / total_sims) * 100

    # 計算莊與閒的期望值 (EV)
    # 莊勝: 1 賠 0.95, 閒勝: 1 賠 1
    ev_b = (b_prob / 100 * 0.95) - (p_prob / 100)
    ev_p = (p_prob / 100 * 1.0) - (b_prob / 100)

    recommend = "觀望 (不建議下注)"
    k_percent = 0.0
    s_bet = 0

    # 1/4 凱利公式計算注碼: f* = (bp - q) / b
    if ev_b > 0 and ev_b > ev_p:
        recommend = "建議下注【莊】"
        full_kelly = ev_b / 0.95
        k_percent = (full_kelly / 4.0) * 100
        s_bet = max(0, int(bankroll * (k_percent / 100)))
    elif ev_p > 0 and ev_p > ev_b:
        recommend = "建議下注【閒】"
        full_kelly = ev_p / 1.0
        k_percent = (full_kelly / 4.0) * 100
        s_bet = max(0, int(bankroll * (k_percent / 100)))

    return avg_tc, b_prob, p_prob, t_prob, recommend, k_percent, s_bet