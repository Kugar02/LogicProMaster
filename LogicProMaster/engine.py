# ==============================================================================
# Quantum Baccarat High-Precision Engine (完全中性權重 + 全路單齊頭對齊 + 觀望避險防禦)
# ==============================================================================
import json
import os

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
                derived.append('Red' if len(cols[c-1]) == len(cols[c-1-k]) else 'Blue')
            else:
                len_ref = len(cols[c-k])
                if len_ref >= r + 1:
                    derived.append('Red')
                elif len_ref == r:
                    derived.append('Blue')
                else:
                    derived.append('Red')
    return derived

# ================= 1. 多階動態馬爾可夫鏈分析器 =================
def analyze_markov_for_sequence(seq, seq_type="BP"):
    n = len(seq)
    if n < 4:
        return 0, None, "樣本不足"
    
    val_a = 'B' if seq_type == "BP" else 'Red'
    val_b = 'P' if seq_type == "BP" else 'Blue'
    lbl_a = '莊' if seq_type == "BP" else '紅'
    lbl_b = '閒' if seq_type == "BP" else '藍'
    
    # 2階馬爾可夫
    last_two = (seq[-2], seq[-1])
    cnt_a2, cnt_b2 = 0, 0
    for i in range(n - 2):
        if (seq[i], seq[i+1]) == last_two:
            nxt = seq[i+2]
            if nxt == val_a: cnt_a2 += 1
            elif nxt == val_b: cnt_b2 += 1
            
    tot2 = cnt_a2 + cnt_b2
    if tot2 >= 2:
        prob_a = cnt_a2 / tot2
        prob_b = cnt_b2 / tot2
        favored = val_a if cnt_a2 > cnt_b2 else (val_b if cnt_b2 > cnt_a2 else 'Neutral')
        net_score = (prob_b - prob_a) * 25.0
        status = f"馬爾可夫(2階/{tot2}局): 前【{last_two[0]},{last_two[1]}】➔ 偏【{'平' if favored=='Neutral' else (lbl_a if favored==val_a else lbl_b)}】"
        return net_score, favored, status
        
    # 1階馬爾可夫
    last_one = seq[-1]
    cnt_a1, cnt_b1 = 0, 0
    for i in range(n - 1):
        if seq[i] == last_one:
            nxt = seq[i+1]
            if nxt == val_a: cnt_a1 += 1
            elif nxt == val_b: cnt_b1 += 1
            
    tot1 = cnt_a1 + cnt_b1
    if tot1 >= 3:
        prob_a = cnt_a1 / tot1
        prob_b = cnt_b1 / tot1
        favored = val_a if cnt_a1 > cnt_b1 else (val_b if cnt_b1 > cnt_a1 else 'Neutral')
        net_score = (prob_b - prob_a) * 15.0
        status = f"馬爾可夫(1階/{tot1}局): 前【{last_one}】➔ 偏【{'平' if favored=='Neutral' else (lbl_a if favored==val_a else lbl_b)}】"
        return net_score, favored, status
        
    return 0, None, "樣本不足"

# ================= 2. 大路極致特徵診斷矩陣 =================
def analyze_big_road_features(clean_hist, feature_weights=None):
    if feature_weights is None:
        feature_weights = {
            'single': 1.0, 'double': 1.0, 'dragon': 1.0, 
            'room': 1.0, 'jump_streak': 1.0, 'head_align': 1.0, 'momentum': 1.0
        }
    n = len(clean_hist)
    b_score, p_score = 0, 0
    details = []
    if n < 3:
        return 0, 0, ["數據不足"]

    # 1. 單跳
    if n >= 3 and clean_hist[-1] != clean_hist[-2] and clean_hist[-2] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        val = 18 * feature_weights.get('single', 1.0)
        if target == 'B': b_score += val
        else: p_score += val
        details.append(f"單跳【{'莊' if target=='B' else '閒'}】")

    # 2. 雙跳
    if n >= 4 and clean_hist[-1] == clean_hist[-2] and clean_hist[-3] == clean_hist[-4] and clean_hist[-1] != clean_hist[-3]:
        target = 'B' if clean_hist[-1] == 'P' else 'P'
        val = 22 * feature_weights.get('double', 1.0)
        if target == 'B': b_score += val
        else: p_score += val
        details.append(f"雙跳【{'莊' if target=='B' else '閒'}】")

    # 3. 長龍
    streak = 1
    for i in range(n-2, -1, -1):
        if clean_hist[i] == clean_hist[-1]:
            streak += 1
        else:
            break
    if streak >= 3:
        target = clean_hist[-1]
        val = (streak * 12) * feature_weights.get('dragon', 1.0)
        if target == 'B': b_score += val
        else: p_score += val
        details.append(f"長龍連{streak}【{'莊' if target=='B' else '閒'}】")

    # 4. 房廳結構
    if n >= 6 and clean_hist[-3:] == clean_hist[-6:-3] and len(set(clean_hist[-3:])) == 2:
        predict_next = clean_hist[-3]
        val = 20 * feature_weights.get('room', 1.0)
        if predict_next == 'B': b_score += val
        else: p_score += val
        details.append(f"房廳週期【{'莊' if predict_next=='B' else '閒'}】")

    # 5. 逢跳連
    if n >= 5:
        jumps_then_streak = True
        for i in range(2, n-1):
            if clean_hist[i] != clean_hist[i-1] and clean_hist[i-1] == clean_hist[i-2]:
                if clean_hist[i+1] != clean_hist[i]:
                    jumps_then_streak = False
                    break
        if jumps_then_streak and clean_hist[-1] != clean_hist[-2]:
            next_target = clean_hist[-1]
            val = 20 * feature_weights.get('jump_streak', 1.0)
            if next_target == 'B': b_score += val
            else: p_score += val
            details.append(f"逢跳連【{'莊' if next_target=='B' else '閒'}】")

    # 6. 大路齊頭對齊
    cols = build_logical_columns(clean_hist)
    if len(cols) >= 3:
        c1, c2 = len(cols[-1]), len(cols[-2])
        if c1 == c2 and c1 >= 2:
            target = 'B' if clean_hist[-1] == 'P' else 'P'
            val = 16 * feature_weights.get('head_align', 1.0)
            if target == 'B': b_score += val
            else: p_score += val
            details.append(f"齊頭對齊【{'莊' if target=='B' else '閒'}】")

    # 7. 短線動能
    recent_6 = clean_hist[-6:]
    b_cnt6, p_cnt6 = recent_6.count('B'), recent_6.count('P')
    if abs(b_cnt6 - p_cnt6) >= 4:
        target = 'B' if b_cnt6 > p_cnt6 else 'P'
        val = 14 * feature_weights.get('momentum', 1.0)
        if target == 'B': b_score += val
        else: p_score += val
        details.append(f"短線爆發【{'莊' if target=='B' else '閒'}】")

    return b_score, p_score, details

# ================= 3. 下三路獨立推導 (單向差值加分) =================
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
    
    # 單向加分判定
    target_trend = 'Red' if red_cnt >= blue_cnt else 'Blue'
    trend_label = "整齊順路(追紅)" if target_trend == 'Red' else "破路跳項(追藍)"
    
    if next_b_symbol == target_trend and next_p_symbol != target_trend:
        b_score += 16
        details.append(trend_label)
    elif next_p_symbol == target_trend and next_b_symbol != target_trend:
        p_score += 16
        details.append(trend_label)

    # 下三路齊頭對齊
    derived_cols = build_logical_columns(derived)
    if len(derived_cols) >= 3:
        dc1, dc2 = len(derived_cols[-1]), len(derived_cols[-2])
        if dc1 == dc2 and dc1 >= 2:
            target_color = 'Blue' if derived[-1] == 'Red' else 'Red'
            if next_b_symbol == target_color and next_p_symbol != target_color:
                b_score += 14
                details.append("齊頭對齊(轉色)")
            elif next_p_symbol == target_color and next_b_symbol != target_color:
                p_score += 14
                details.append("齊頭對齊(轉色)")

    # 馬爾可夫鏈預測
    mc_score, mc_favored, mc_status = analyze_markov_for_sequence(derived, seq_type="RedBlue")
    if mc_favored == 'Red':
        if next_b_symbol == 'Red' and next_p_symbol != 'Red':
            b_score += 18
            details.append("馬爾可夫預測【紅】")
        elif next_p_symbol == 'Red' and next_b_symbol != 'Red':
            p_score += 18
            details.append("馬爾可夫預測【紅】")
    elif mc_favored == 'Blue':
        if next_b_symbol == 'Blue' and next_p_symbol != 'Blue':
            b_score += 18
            details.append("馬爾可夫預測【藍】")
        elif next_p_symbol == 'Blue' and next_b_symbol != 'Blue':
            p_score += 18
            details.append("馬爾可夫預測【藍】")
        
    if b_score > p_score:
        dominant, net_score = 'B', -(b_score - p_score)
        status = f"🔴 莊強 (莊{b_score:.0f} vs 閒{p_score:.0f})"
    elif p_score > b_score:
        dominant, net_score = 'P', (p_score - b_score)
        status = f"🔵 閒強 (閒{p_score:.0f} vs 莊{b_score:.0f})"
    else:
        dominant, net_score = 'Neutral', 0
        status = "⚪ 導出訊號持平"
        
    if mc_status and "樣本不足" not in mc_status:
        details.append(mc_status)
        
    return {'name': road_name, 'dominant': dominant, 'net_score': net_score, 'status': status, 'details': details}

# ================= 4. AI 線上勝率追蹤與動態 EMA 調權 =================
def compute_ai_online_learning(history_list):
    clean_hist = [x for x in history_list if x in ['B', 'P']]
    n = len(clean_hist)
    core_hits = {'big_road': 0, 'big_eye': 0, 'small_road': 0, 'roach_road': 0}
    core_totals = {'big_road': 0, 'big_eye': 0, 'small_road': 0, 'roach_road': 0}

    base_weights = {'big_road': 0.40, 'big_eye': 0.20, 'small_road': 0.20, 'roach_road': 0.20}
    if os.path.exists("drive_weights.json"):
        try:
            with open("drive_weights.json", "r") as f:
                saved = json.load(f)
                if 'base_weights' in saved:
                    base_weights = saved['base_weights']
        except Exception:
            pass

    if n >= 6:
        valid_indices = [idx for idx, item in enumerate(history_list) if item in ['B', 'P']]
        for i in range(5, n):
            past = clean_hist[:i]
            actual = clean_hist[i]

            b_s, p_s, _ = analyze_big_road_features(past)
            pred_big = 'B' if b_s > p_s else ('P' if p_s > b_s else None)
            if pred_big:
                core_totals['big_road'] += 1
                if pred_big == actual:
                    core_hits['big_road'] += 1

            raw_past_end = valid_indices[i - 1] + 1 if i - 1 < len(valid_indices) else len(history_list)
            raw_past = history_list[:raw_past_end]

            for k, key in [(1, 'big_eye'), (2, 'small_road'), (3, 'roach_road')]:
                res = analyze_derived_road_core(raw_past, k, key)
                if res['dominant'] != 'Neutral':
                    core_totals[key] += 1
                    if res['dominant'] == actual:
                        core_hits[key] += 1

    dynamic_core_weights = {}
    for key in base_weights:
        tot = core_totals[key]
        if tot > 0:
            accuracy = core_hits[key] / tot
            multiplier = max(0.2, min(2.0, accuracy / 0.50))
        else:
            multiplier = 1.0
        dynamic_core_weights[key] = base_weights[key] * multiplier

    tot_w = sum(dynamic_core_weights.values())
    if tot_w > 0:
        for key in dynamic_core_weights:
            dynamic_core_weights[key] /= tot_w

    feature_weights = {
        'single': 1.0, 'double': 1.0, 'dragon': 1.0, 
        'room': 1.0, 'jump_streak': 1.0, 'head_align': 1.0, 'momentum': 1.0
    }
    return dynamic_core_weights, feature_weights

# ================= 5. 四大路綜合診斷與三路共振 =================
def analyze_four_core_roads(history):
    clean_hist = [x for x in history if x in ['B', 'P']]
    total_hands = len(history)

    dynamic_core_weights, feature_weights = compute_ai_online_learning(history)

    b_score_big, p_score_big, det_big = analyze_big_road_features(clean_hist, feature_weights)
    big_mc_score, big_mc_fav, big_mc_status = analyze_markov_for_sequence(clean_hist, seq_type="BP")

    if big_mc_fav == 'B': b_score_big += 18
    elif big_mc_fav == 'P': p_score_big += 18

    if "樣本不足" not in big_mc_status:
        det_big.append(big_mc_status)

    if b_score_big > p_score_big:
        dom_big, net_big = 'B', -(b_score_big - p_score_big)
        status_big = f"🔴 莊強 (莊{b_score_big:.0f} vs 閒{p_score_big:.0f})"
    elif p_score_big > b_score_big:
        dom_big, net_big = 'P', (p_score_big - b_score_big)
        status_big = f"🔵 閒強 (閒{p_score_big:.0f} vs 莊{b_score_big:.0f})"
    else:
        dom_big, net_big = 'Neutral', 0
        status_big = "⚪ 訊號持平"

    big_pct_str = f"{dynamic_core_weights['big_road']*100:.0f}%"
    big_road_res = {'name': f'1. 大路核心 (AI動態:{big_pct_str})', 'dominant': dom_big, 'net_score': net_big, 'status': status_big, 'details': det_big}

    big_eye_pct = f"{dynamic_core_weights['big_eye']*100:.0f}%"
    big_eye_res = analyze_derived_road_core(history, k=1, road_name=f'2. 大眼仔路 (AI動態:{big_eye_pct})')

    small_pct = f"{dynamic_core_weights['small_road']*100:.0f}%"
    small_road_res = analyze_derived_road_core(history, k=2, road_name=f'3. 小路核心 (AI動態:{small_pct})')

    roach_pct = f"{dynamic_core_weights['roach_road']*100:.0f}%"
    roach_road_res = analyze_derived_road_core(history, k=3, road_name=f'4. 曱甴路核心 (AI動態:{roach_pct})')

    roads = {
        'big_road': big_road_res,
        'big_eye': big_eye_res,
        'small_road': small_road_res,
        'roach_road': roach_road_res
    }

    derived_discount = 0.3 if net_big == 0 else 1.0
    if total_hands < 10:
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
        weighted_score *= 2.2
        for key in ['big_eye', 'small_road', 'roach_road']:
            roads[key]['status'] += " (🔥三路極致共振)"

    valid_dominants = [r['dominant'] for r in roads.values() if r['dominant'] != 'Neutral']
    if valid_dominants:
        most_common = max(set(valid_dominants), key=valid_dominants.count)
        confidence_pct = round((valid_dominants.count(most_common) / len(valid_dominants)) * 100)
    else:
        confidence_pct = 50

    return roads, weighted_score, is_resonance, confidence_pct

# ================= 6. 主引擎入口 (嚴格返回 11 個參數) =================
def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None):
    b_count = int(b_count) if b_count is not None else 0
    p_count = int(p_count) if p_count is not None else 0
    t_count = int(t_count) if t_count is not None else 0
    history_list = list(history_list) if history_list is not None else []
    ai_targets = list(ai_targets) if ai_targets is not None else []
    
    total_hands = b_count + p_count + t_count

    four_roads, weighted_road_score, is_resonance, confidence_pct = analyze_four_core_roads(history_list)

    consecutive_losses = 0
    if ai_targets and history_list:
        for tgt, actual in zip(reversed(ai_targets), reversed(history_list)):
            target_val = tgt.get('target') if isinstance(tgt, dict) else tgt
            if target_val and actual != 'T':
                if target_val != actual:
                    consecutive_losses += 1
                else:
                    break

    is_break_active = False
    if confidence_pct >= 68 or is_resonance:
        is_break_active = False
        final_score = weighted_road_score
    elif consecutive_losses >= 2 or confidence_pct < 40:
        is_break_active = True
        final_score = -weighted_road_score * 0.8
    else:
        final_score = weighted_road_score

    BASE_B, BASE_P = 50.0, 50.0

    macro_skew = (b_count - p_count) * 0.10
    road_weight_bias = (final_score / 100.0) * 22.0

    l2_b = BASE_B - road_weight_bias + macro_skew
    l2_p = BASE_P + road_weight_bias - macro_skew

    actual_t_ratio = (t_count / total_hands * 100) if total_hands > 0 else 9.52
    tie_implicit_bias = (actual_t_ratio - 9.52) * 0.10

    post_b = l2_b - tie_implicit_bias
    post_p = l2_p + tie_implicit_bias

    if final_score == 0 and macro_skew == 0:
        post_b += 0.5

    total_weight = max(0.001, post_b + post_p)
    final_b_pct = round((post_b / total_weight) * 100, 1)
    final_p_pct = round((post_p / total_weight) * 100, 1)

    margin_diff = abs(final_b_pct - final_p_pct)
    
    if is_resonance:
        if final_b_pct >= final_p_pct:
            recommend = "🔥 三路共振極致出擊【莊】"
        else:
            recommend = "🔥 三路共振極致出擊【閒】"
    elif confidence_pct < 52 or margin_diff < 1.8:
        recommend = "⏸️ 訊號混亂 (建議觀望避險)"
    elif final_b_pct >= final_p_pct:
        recommend = "⚔️ 智能反打【莊】" if is_break_active else "🔥 強勢正打【莊】"
    else:
        recommend = "⚔️ 智能反打【閒】" if is_break_active else "🔥 強勢正打【閒】"

    status_msg = f"[高精準純特徵引擎] 完全中性基準 ｜ 牌靴偏態: {macro_skew:+.1f}%"
    
    return 0.0, final_b_pct, final_p_pct, round(actual_t_ratio, 1), recommend, four_roads, is_break_active, consecutive_losses, status_msg, is_resonance, confidence_pct
