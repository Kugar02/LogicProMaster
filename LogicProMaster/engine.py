# ==============================================================================
# Quantum Baccarat Engine - dynamic shoe adaptation, feature ranking and volatility
# ==============================================================================

DEFAULT_FEATURE_WEIGHTS = {
    'single': 1.0, 'double': 1.0, 'dragon': 1.0,
    'room': 1.0, 'jump_streak': 1.0, 'row_row_streak': 1.0,
}


def build_logical_columns(history):
    cols, current, last = [], [], None
    for result in history:
        if result == 'T':
            continue
        if result != last:
            if current:
                cols.append(current)
            current, last = [result], result
        else:
            current.append(result)
    if current:
        cols.append(current)
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
                derived.append('Red' if ref_len >= r + 1 or ref_len < r else 'Blue')
    return derived


def analyze_markov_for_sequence(seq, seq_type='BP'):
    if len(seq) < 4:
        return 0.0, None, '樣本不足'
    a, b = ('B', 'P') if seq_type == 'BP' else ('Red', 'Blue')
    last_two = (seq[-2], seq[-1])
    count_a = count_b = 0
    for i in range(len(seq) - 2):
        if (seq[i], seq[i + 1]) == last_two:
            count_a += seq[i + 2] == a
            count_b += seq[i + 2] == b
    total = count_a + count_b
    if total < 3:
        return 0.0, None, f'樣本不足({total}次)'
    favored = a if count_a > count_b else b if count_b > count_a else 'Neutral'
    score = (count_a - count_b) * 20.0
    labels = ('莊', '閒') if seq_type == 'BP' else ('紅', '藍')
    label = '平' if favored == 'Neutral' else labels[0] if favored == a else labels[1]
    return score, favored, f'馬爾可夫({total}局): 前【{last_two[0]},{last_two[1]}】➔ 偏【{label}】'


def _feature(side, value, name, description=''):
    return {'feature': name, 'side': side, 'value': round(float(value), 2), 'description': description}


def analyze_big_road_features(clean_hist, feature_weights=None):
    weights = {**DEFAULT_FEATURE_WEIGHTS, **(feature_weights or {})}
    b_score = p_score = 0.0
    features = []
    n = len(clean_hist)
    if n < 3:
        return 0.0, 0.0, ['數據不足'], []

    def add(target, value, name, description=''):
        nonlocal b_score, p_score
        if target == 'B': b_score += value
        else: p_score += value
        features.append(_feature(target, value if target == 'B' else -value, name, description))

    if clean_hist[-1] != clean_hist[-2] and clean_hist[-2] != clean_hist[-3]:
        add('B' if clean_hist[-1] == 'P' else 'P', 15 * weights['single'], '單跳')
    if n >= 4 and clean_hist[-1] == clean_hist[-2] and clean_hist[-3] == clean_hist[-4] and clean_hist[-1] != clean_hist[-3]:
        add('B' if clean_hist[-1] == 'P' else 'P', 20 * weights['double'], '雙跳')

    run = 1
    for i in range(n - 2, -1, -1):
        if clean_hist[i] == clean_hist[-1]: run += 1
        else: break
    if run >= 3:
        add(clean_hist[-1], run * 10 * weights['dragon'], f'長龍連{run}')

    if n >= 6 and clean_hist[-3:] == clean_hist[-6:-3] and len(set(clean_hist[-3:])) == 2:
        add(clean_hist[-3], 16 * weights['room'], '房廳')

    # 逢跳連：最近多次「一對後轉邊」都按同一方向延續。
    if n >= 5:
        valid = True
        for i in range(2, n - 1):
            if clean_hist[i] != clean_hist[i - 1] and clean_hist[i - 1] == clean_hist[i - 2]:
                if clean_hist[i + 1] != clean_hist[i]:
                    valid = False
                    break
        if valid and clean_hist[-1] != clean_hist[-2]:
            add(clean_hist[-1], 18 * weights['jump_streak'], '逢跳連')

    # 排排連：最近至少兩組相同長度的連續排列，視為獨立的連續結構特徵。
    runs = []
    for result in clean_hist:
        if not runs or runs[-1][0] != result:
            runs.append([result, 1])
        else:
            runs[-1][1] += 1
    row_streak = 0
    if len(runs) >= 3:
        for i in range(len(runs) - 1, 0, -1):
            if runs[i][1] == runs[i - 1][1]: row_streak += 1
            else: break
    if row_streak >= 2:
        target = runs[-1][0]
        add(target, (12 + row_streak * 4) * weights['row_row_streak'], f'排排連×{row_streak}')

    details = [f"{x['feature']}【{'莊' if x['side'] == 'B' else '閒'} {x['value']:+.1f}】" for x in features]
    return b_score, p_score, details, sorted(features, key=lambda x: abs(x['value']), reverse=True)


def analyze_derived_road_core(history, k, road_name):
    derived = get_derived_road(build_logical_columns(history), k)
    if not derived:
        return {'name': road_name, 'dominant': 'Neutral', 'net_score': 0, 'status': '⚪ 無路可參考', 'details': ['下三路未開出'], 'feature_ranking': []}
    recent = derived[-6:]
    wanted = 'Red' if recent.count('Red') >= recent.count('Blue') else 'Blue'
    next_b = get_derived_road(build_logical_columns(history + ['B']), k)
    next_p = get_derived_road(build_logical_columns(history + ['P']), k)
    next_b = next_b[-1] if next_b else None
    next_p = next_p[-1] if next_p else None
    b_score = 12 if next_b == wanted else 0
    p_score = 12 if next_p == wanted else 0
    features = []
    if b_score: features.append(_feature('B', b_score, '順路/破路'))
    if p_score: features.append(_feature('P', -p_score, '順路/破路'))
    _, favored, mc_status = analyze_markov_for_sequence(derived, 'RedBlue')
    if favored in ('Red', 'Blue'):
        b_add, p_add = (15 if next_b == favored else 0), (15 if next_p == favored else 0)
        if b_add: features.append(_feature('B', b_add, '馬爾可夫'))
        if p_add: features.append(_feature('P', -p_add, '馬爾可夫'))
        b_score += b_add; p_score += p_add
    if b_score > p_score:
        dominant, net = 'B', b_score - p_score
        status = f'🔴 莊強 (莊{b_score:.0f} vs 閒{p_score:.0f})'
    elif p_score > b_score:
        dominant, net = 'P', -(p_score - b_score)
        status = f'🔵 閒強 (閒{p_score:.0f} vs 莊{b_score:.0f})'
    else:
        dominant, net, status = 'Neutral', 0, '⚪ 導出訊號持平'
    details = [('整齊順路(追紅)' if wanted == 'Red' else '破路跳項(追藍)')]
    if '樣本不足' not in mc_status: details.append(mc_status)
    return {'name': road_name, 'dominant': dominant, 'net_score': net, 'status': status, 'details': details, 'feature_ranking': sorted(features, key=lambda x: abs(x['value']), reverse=True)}


def _raw_core_snapshot(history):
    clean = [x for x in history if x in ('B', 'P')]
    b, p, _, _ = analyze_big_road_features(clean)
    _, fav, _ = analyze_markov_for_sequence(clean, 'BP')
    if fav == 'B': b += 15
    elif fav == 'P': p += 15
    roads = {'big_road': b - p}
    for k, key in ((1, 'big_eye'), (2, 'small_road'), (3, 'roach_road')):
        roads[key] = analyze_derived_road_core(history, k, key)['net_score']
    return roads


def compute_dynamic_thresholds(history, window=50, alpha=0.2, min_samples=8):
    snapshots = []
    for i in range(1, len(history) + 1):
        snapshots.append(_raw_core_snapshot(history[:i]))
    keys = ('big_road', 'big_eye', 'small_road', 'roach_road')
    thresholds = {}
    for key in keys:
        values = [row[key] for row in snapshots if row[key] != 0][-window:]
        if len(values) < min_samples:
            thresholds[key] = {'medium': 12.0, 'strong': 24.0, 'samples': len(values), 'consecutive': 0}
            continue
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        thresholds[key] = {'medium': max(8.0, abs(mean) + 0.6 * std), 'strong': max(16.0, abs(mean) + 1.25 * std), 'samples': len(values), 'consecutive': 0}
    return thresholds


def _strength(confidence, score, thresholds):
    strong = max((v['strong'] for v in thresholds.values()), default=24.0)
    medium = max((v['medium'] for v in thresholds.values()), default=12.0)
    if confidence >= 75 and abs(score) >= strong: return '強訊號'
    if confidence >= 50 and abs(score) >= medium: return '中訊號'
    return '弱訊號'


def analyze_four_core_roads(history, window=50, alpha=0.2):
    clean = [x for x in history if x in ('B', 'P')]
    thresholds = compute_dynamic_thresholds(history, window, alpha)
    weights = {'big_road': .40, 'big_eye': .20, 'small_road': .20, 'roach_road': .20}
    b, p, details, ranking = analyze_big_road_features(clean)
    _, fav, mc_status = analyze_markov_for_sequence(clean, 'BP')
    if fav == 'B': b += 15
    elif fav == 'P': p += 15
    if '樣本不足' not in mc_status: details.append(mc_status)
    big_net = b - p
    big_dom = 'B' if big_net > 0 else 'P' if big_net < 0 else 'Neutral'
    roads = {'big_road': {'name': '1. 大路核心', 'dominant': big_dom, 'net_score': big_net, 'status': f"{'🔴 莊強' if big_dom == 'B' else '🔵 閒強' if big_dom == 'P' else '⚪ 持平'} (莊{b:.0f} vs 閒{p:.0f})", 'details': details, 'feature_ranking': ranking}}
    for k, key, label in ((1, 'big_eye', '大眼仔路'), (2, 'small_road', '小路核心'), (3, 'roach_road', '曱甴路核心')):
        roads[key] = analyze_derived_road_core(history, k, f'{k + 1}. {label}')
    valid = [r['dominant'] for r in roads.values() if r['dominant'] != 'Neutral']
    confidence = round(max(valid.count('B'), valid.count('P')) / len(valid) * 100) if valid else 50
    discount = 0.0 if len(history) < 12 else (0.3 if big_net == 0 else 1.0)
    score = sum(roads[k]['net_score'] * weights[k] * (1 if k == 'big_road' else discount) for k in roads)
    dominant = [roads[k]['dominant'] for k in ('big_eye', 'small_road', 'roach_road')]
    resonance = dominant.count('B') == 3 or dominant.count('P') == 3
    if resonance: score *= 1.4
    level = _strength(confidence, score, thresholds)
    for key, road in roads.items():
        road['signal_strength'] = _strength(100 if road['dominant'] != 'Neutral' else 50, road['net_score'], {key: thresholds[key]})
    return roads, score, resonance, confidence, level, thresholds, discount


def get_engine_diagnostics(history, ai_targets=None, window=50, alpha=0.2):
    ai_targets = ai_targets or []
    points = []
    for i in range(1, len(history) + 1):
        roads, score, resonance, confidence, level, thresholds, discount = analyze_four_core_roads(history[:i], window, alpha)
        point = {'局數': i, 'weighted_score': round(score, 2), 'confidence': confidence}
        for key in ('big_road', 'big_eye', 'small_road', 'roach_road'):
            point[key] = roads[key]['net_score']
        points.append(point)
    return points


def run_monte_carlo_with_kelly(b_count, p_count, t_count, bankroll=10000, sim_count=100000, history_list=None, ai_targets=None, window=50, alpha=0.2):
    history_list = history_list or []
    ai_targets = ai_targets or []
    total = b_count + p_count + t_count
    natural_b, natural_p, natural_t = 45.86, 44.62, 9.52
    roads, score, resonance, confidence, level, thresholds, discount = analyze_four_core_roads(history_list, window, alpha)
    losses = 0
    for target, actual in zip(reversed(ai_targets), reversed(history_list)):
        if target and target.get('target') and actual != 'T':
            if target['target'] != actual: losses += 1
            else: break

    # dynamic loss threshold based on window (larger window -> slightly larger tolerance)
    dynamic_loss_thresh = max(2, int(max(2, window / 25)))

    # dynamic break logic to avoid single/brief dips causing immediate反打
    if confidence < 25:
        break_active = True
    else:
        if level == '強訊號':
            break_active = False
        elif level == '中訊號':
            break_active = (confidence < 50 and losses >= dynamic_loss_thresh)
        else:  # 弱訊號
            break_active = (confidence < 55 and losses >= max(1, dynamic_loss_thresh - 1))

    # force-break if persistent losses exceed threshold regardless of level
    if losses >= dynamic_loss_thresh and confidence < 65:
        break_active = True

    final_score = -score * .75 if break_active else score
    macro_skew = (p_count - b_count) * .15
    bias = final_score / 100 * 15
    l2_b, l2_p = natural_b + bias - macro_skew, natural_p - bias + macro_skew
    tie_bias = (((t_count / total * 100) if total else natural_t) - natural_t) * .15
    post_b, post_p = l2_b - tie_bias, l2_p + tie_bias
    denom = max(.001, post_b + post_p)
    final_b, final_p = round(post_b / denom * 100, 1), round(post_p / denom * 100, 1)
    side = '莊' if final_b >= final_p else '閒'
    recommend = f"{'⚔️ 智能反打' if break_active else '🔥 強勢正打'}【{side}】"
    status = f'[動態牌靴分析] {level} ｜ EMA α={alpha:.2f} ｜ 牌靴偏態: {macro_skew:+.1f}%'

    # return additional diagnostics: level & thresholds for UI
    return 0.0, final_b, final_p, round((t_count / total * 100) if total else natural_t, 1), recommend, roads, break_active, losses, status, resonance, confidence, level, thresholds
