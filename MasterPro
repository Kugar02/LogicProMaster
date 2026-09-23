/**
 * 百家樂多維路單與 AI 預測核心引擎 (模組化優化版)
 * 包含：四大路單引擎、問路系統、12大AI權重邏輯
 */
const BaccaratApp = (function() {
    // --- 狀態管理 (State) ---
    const state = {
        history: [],
        MAX_HANDS: 100
    };

    // --- 1. 路單運算模組 (RoadMap Engine) ---
    const RoadMap = {
        // 構建大路
        buildBigRoad(history) {
            let grid = [], curCol = -1, lastColor = null, tieCount = 0;
            history.forEach(res => {
                if (res === 'T') {
                    if (curCol === -1) tieCount++;
                    else gridcurCol.length - 1].ties++;
                } else {
                    if (res !== lastColor) {
                        curCol++;
                        grid[curCol] = [];
                        lastColor = res;
                    }
                    grid[curCol].push({ color: res === 'B' ? 'RED' : 'BLUE', ties: tieCount });
                    tieCount = 0;
                }
            });
            return grid;
        },
        // 構建下三路 (大眼仔=1, 小路=2, 曱甴路=3)
        getDerivedSequence(bigRoadMatrix, offset) {
            let seq = [];
            for (let col = 1; col < bigRoadMatrix.length; col++) {
                for (let row = 0; row < bigRoadMatrix[col].length; row++) {
                    if (row === 0 && col < offset + 1) continue;
                    
                    let isRed = false;
                    if (row === 0) {
                        let lenPrev = bigRoadMatrix[col - 1].length;
                        let lenCompare = bigRoadMatrix[col - 1 - offset] ? bigRoadMatrix[col - 1 - offset].length : 0;
                        isRed = (lenPrev === lenCompare);
                    } else {
                        let lenCompare = bigRoadMatrix[col - offset] ? bigRoadMatrix[col - offset].length : 0;
                        isRed = (row < lenCompare) ? true : (row === lenCompare ? false : true);
                    }
                    seq.push(isRed ? 'RED' : 'BLUE');
                }
            }
            return seq;
        },
        // 矩陣/陣列 轉 長度序列 (供 AI 分析)
        matrixToLengths(matrix) { return matrix.map(col => col.length); },
        seqToLengths(seq) {
            if (!seq.length) return [];
            let lengths = [], cur = 1, last = seq[0];
            for (let i = 1; i < seq.length; i++) {
                if (seq[i] === last) cur++;
                else { lengths.push(cur); cur = 1; last = seq[i]; }
            }
            lengths.push(cur);
            return lengths;
        },
        // 陣列轉矩陣 (供 UI 渲染)
        seqToMatrix(seq) {
            let m = [], c = -1, last = null;
            seq.forEach(color => {
                if (color !== last) { c++; m[c] = []; last = color; }
                m[c].push(color);
            });
            return m;
        }
    };

    // --- 2. 莊閒問路模組 (Ask Road) ---
    const AskRoad = {
        getNextAskDots(history, nextResult) {
            let testHistory = [...history, nextResult];
            let br = RoadMap.buildBigRoad(testHistory);
            let be = RoadMap.getDerivedSequence(br, 1);
            let sm = RoadMap.getDerivedSequence(br, 2);
            let ro = RoadMap.getDerivedSequence(br, 3);
            return {
                bigEye: be.length ? be[be.length - 1] : null,
                small: sm.length ? sm[sm.length - 1] : null,
                roach: ro.length ? ro[ro.length - 1] : null
            };
        }
    };

    // --- 3. 核心 12 大 AI 邏輯權重引擎 ---
    const AIEngine = {
        analyze(lengthsArray, currentColor) {
            if (lengthsArray.length < 3) return null;
            let len = lengthsArray.length;
            let currentL = lengthsArray[len - 1];
            let prev1 = lengthsArray[len - 2];
            let prev2 = lengthsArray[len - 3];
            let prev3 = len > 3 ? lengthsArray[len - 4] : 0;
            
            let oppositeColor = currentColor === 'RED' ? 'BLUE' : 'RED';
            let predictions = [];

            const addRule = (name, target, weight, alertMsg = "") => {
                predictions.push({ name, target, weight, alertMsg });
            };

            // 【邏輯一】單跳
            if (currentL === 1) {
                let jumpCount = 1;
                for (let i = len - 2; i >= 0; i--) { if (lengthsArray[i] === 1) jumpCount++; else break; }
                if (jumpCount >= 2) {
                    if (jumpCount <= 3) addRule('邏輯一「單跳」(短)', oppositeColor, 10);
                    else if (jumpCount <= 5) addRule('邏輯一「單跳」(中)', oppositeColor, 15);
                    else addRule('邏輯一「單跳」(長-極限危險)', currentColor, 25, '⚠ 破路反打觸發：單跳達極限，強制反打');
                }
            }

            // 【邏輯二】雙跳
            if (currentL === 2) {
                let doubleCount = 0;
                for (let i = len - 1; i >= 0; i--) { if (lengthsArray[i] === 2) doubleCount++; else break; }
                if (doubleCount >= 2) {
                    if (doubleCount === 2) addRule('邏輯二「雙跳」(短)', oppositeColor, 10);
                    else if (doubleCount === 3) addRule('邏輯二「雙跳」(中)', oppositeColor, 15);
                    else addRule('邏輯二「雙跳」(長-極限危險)', currentColor, 25, '⚠ 破路反打觸發：雙跳達極限，預測破壞');
                }
            } else if (currentL === 1 && prev1 === 2 && prev2 === 2) {
                addRule('邏輯二「雙跳」(延續)', currentColor, 12);
            }

            // 【邏輯三】龍
            if (currentL >= 3) {
                if (currentL <= 4) addRule('邏輯三「龍」(短)', currentColor, 12);
                else if (currentL <= 6) addRule('邏輯三「龍」(中)', currentColor, 18);
                else addRule('邏輯三「龍」(長-極限危險)', oppositeColor, 30, '⚠ 破路反打觸發：長龍極限斷路預測');
            }

            // 【邏輯四】房廳 (2-1-2)
            if (prev2 === 2 && prev1 === 1 && currentL === 1) addRule('邏輯四「房廳」(2-1-2 補齊)', currentColor, 12);
            else if (prev3 === 2 && prev2 === 2 && prev1 === 1 && currentL === 1) addRule('邏輯四「房廳」(破壞反打)', oppositeColor, 15, '⚠ 房廳極限邊界反打');

            // 【邏輯五】逢跳連
            if (currentL === 1 && prev1 > 1) addRule('邏輯五「逢跳連」', currentColor, 15);

            // 【進階特規邏輯六 ~ 十二】
            if (prev1 === 3 && currentL === 1) addRule('邏輯六「3-2補齊」', currentColor, 20);
            if (prev1 === 3 && currentL === 3) addRule('邏輯七「3-3反打」', oppositeColor, 20);
            if (prev2 === 3 && prev1 === 3 && currentL === 1) addRule('邏輯八「3-3-2補齊」', currentColor, 20);
            if (prev1 === 2 && currentL === 3) addRule('邏輯九「2-3反打」', oppositeColor, 20);
            if (prev2 === 3 && prev1 === 3 && currentL === 3) addRule('邏輯十「3-3-3反打」', oppositeColor, 30, '⚠ 3-3-3 強制反打');
            if (prev2 === 1 && prev1 === 3 && currentL === 1) addRule('邏輯十一「1-3-1反打」', oppositeColor, 22);
            if (prev2 === 3 && prev1 === 1 && currentL === 3) addRule('邏輯十二「3-1-3反打」', oppositeColor, 25);

            if (predictions.length === 0) return null;

            // 結算當前引擎權重
            let scoreRED = 0, scoreBLUE = 0;
            predictions.forEach(p => p.target === 'RED' ? scoreRED += p.weight : scoreBLUE += p.weight);
            
            return {
                predictions,
                scoreRED,
                scoreBLUE,
                finalColor: scoreRED > scoreBLUE ? 'RED' : (scoreBLUE > scoreRED ? 'BLUE' : 'N')
            };
        }
    };

    // --- 4. 畫面渲染與 UI 控制模組 ---
    const UI = {
        updateAll() {
            this.updateBasicStats();
            let bigRoad = RoadMap.buildBigRoad(state.history);
            let beSeq = RoadMap.getDerivedSequence(bigRoad, 1);
            let smSeq = RoadMap.getDerivedSequence(bigRoad, 2);
            let roSeq = RoadMap.getDerivedSequence(bigRoad, 3);

            this.renderGrid('roadBigRoad', bigRoad, 'bigroad');
            this.renderGrid('roadBigEye', RoadMap.seqToMatrix(beSeq), 'derived');
            this.renderGrid('roadSmall', RoadMap.seqToMatrix(smSeq), 'derived');
            this.renderGrid('roadCockroach', RoadMap.seqToMatrix(roSeq), 'derived');

            let askData = this.updateAskRoad();
            this.runAIDashboard(bigRoad, beSeq, smSeq, roSeq, askData);
        },
        updateBasicStats() {
            let counts = {B:0, P:0, T:0};
            let histHtml = '';
            state.history.forEach(r => {
                counts[r]++;
                histHtml += `<div class="badge-box badge-box-${r}">${r}</div>`;
            });
            document.getElementById('countB').innerText = counts.B;
            document.getElementById('countP').innerText = counts.P;
            document.getElementById('countT').innerText = counts.T;
            document.getElementById('beadCountInfo').innerText = `總局數: ${state.history.length}/${state.MAX_HANDS}`;
            document.getElementById('historyList').innerHTML = histHtml;
        },
        renderGrid(containerId, matrix, type) {
            const container = document.getElementById(containerId);
            container.innerHTML = '';
            let maxCols = Math.max(16, matrix.length + 2);
            
            for (let c = 0; c < maxCols; c++) {
                let colDiv = document.createElement('div');
                colDiv.className = 'road-col';
                for (let r = 0; r < 6; r++) {
                    let cell = document.createElement('div');
                    cell.className = 'road-cell';
                    let dot = document.createElement('span');
                    dot.className = 'mini-dot empty';
                    
                    if (matrix[c] && matrix[c][r]) {
                        let item = matrix[c][r];
                        let colorClass = typeof item === 'string' ? (item === 'RED' ? 'red' : 'blue') : (item.color === 'RED' ? 'red' : 'blue');
                        dot.className = `mini-dot ${colorClass}`;
                        
                        if (item.ties > 0 && type === 'bigroad') {
                            let tInd = document.createElement('div');
                            tInd.className = 'tie-indicator';
                            if (item.ties > 1) {
                                let tTxt = document.createElement('span');
                                tTxt.className = 'tie-text';
                                tTxt.innerText = item.ties;
                                tInd.appendChild(tTxt);
                            }
                            dot.appendChild(tInd);
                        }
                    }
                    cell.appendChild(dot);
                    colDiv.appendChild(cell);
                }
                container.appendChild(colDiv);
            }
        },
        updateAskRoad() {
            let resB = AskRoad.getNextAskDots(state.history, 'B');
            let resP = AskRoad.getNextAskDots(state.history, 'P');
            
            const applyDot = (id, type, color) => {
                let el = document.getElementById(id);
                if (!color) {
                    el.className = 'ask-dot empty';
                    el.style = '';
                } else {
                    let colClass = color === 'RED' ? 'red' : 'blue';
                    let baseTypeClass = type === 1 ? 'type-bigeye' : type === 2 ? 'type-small' : 'type-roach';
                    el.className = `mini-dot ${colClass} ${baseTypeClass}`;
                    
                    if (type === 1) { el.style.border = `2px solid ${color==='RED'?'var(--banker-color)':'var(--player-color)'}`; el.style.backgroundColor = 'transparent'; }
                    if (type === 2) { el.style.backgroundColor = color==='RED'?'var(--banker-color)':'var(--player-color)'; el.style.border = 'none'; }
                    if (type === 3) { 
                        let c = color==='RED'?'var(--banker-color)':'var(--player-color)';
                        el.style.background = `linear-gradient(45deg, transparent 40%, ${c} 40%, ${c} 60%, transparent 60%)`;
                        el.style.border = `1px solid ${c}`;
                    }
                }
            };

            applyDot('askBigEyeB', 1, resB.bigEye); applyDot('askSmallB', 2, resB.small); applyDot('askRoachB', 3, resB.roach);
            applyDot('askBigEyeP', 1, resP.bigEye); applyDot('askSmallP', 2, resP.small); applyDot('askRoachP', 3, resP.roach);
            
            return { B: resB, P: resP };
        },
        runAIDashboard(bigRoad, beSeq, smSeq, roSeq, askData) {
            let brLengths = RoadMap.matrixToLengths(bigRoad);
            let beLengths = RoadMap.seqToLengths(beSeq);
            let smLengths = RoadMap.seqToLengths(smSeq);
            let roLengths = RoadMap.seqToLengths(roSeq);

            let lastBrColor = bigRoad.length > 0 ? bigRoad[bigRoad.length-1][0].color : null;
            let lastBeColor = beSeq.length > 0 ? beSeq[beSeq.length-1] : null;
            let lastSmColor = smSeq.length > 0 ? smSeq[smSeq.length-1] : null;
            let lastRoColor = roSeq.length > 0 ? roSeq[roSeq.length-1] : null;

            let resBR = AIEngine.analyze(brLengths, lastBrColor);
            let resBE = AIEngine.analyze(beLengths, lastBeColor);
            let resSM = AIEngine.analyze(smLengths, lastSmColor);
            let resRO = AIEngine.analyze(roLengths, lastRoColor);

            let gridHtml = '';
            let finalVotes = { B: 0, P: 0 };
            let reasonText = '';

            const processCore = (name, res, askMapping) => {
                if (!res) {
                    gridHtml += `<div class="analysis-card"><div class="card-header"><span class="card-title">${name}</span></div><div class="section-content">數據不足，持續觀望。</div></div>`;
                    return;
                }

                let finalTargetBP = 'N';
                if (res.finalColor !== 'N') {
                    if (askMapping && askMapping.B === res.finalColor) finalTargetBP = 'B';
                    else if (askMapping && askMapping.P === res.finalColor) finalTargetBP = 'P';
                    else if (!askMapping) {
                        if (res.finalColor === 'RED') finalTargetBP = lastBrColor === 'RED' ? 'B' : 'P';
                        else finalTargetBP = lastBrColor === 'RED' ? 'P' : 'B';
                    }
                    
                    if (finalTargetBP === 'B') finalVotes.B += Math.max(res.scoreRED, res.scoreBLUE);
                    if (finalTargetBP === 'P') finalVotes.P += Math.max(res.scoreRED, res.scoreBLUE);
                }

                let rulesHtml = res.predictions.map(p => `
                    <div class="section-box">
                        <div style="display:flex; justify-content:space-between;">
                            <span class="section-title">${p.name}</span>
                            <span class="card-weight">權重 +${p.weight}</span>
                        </div>
                        <div style="color:${p.target==='RED'?'#f87171':'#60a5fa'}; font-size:0.75rem; font-weight:bold;">指向: ${p.target}</div>
                        ${p.alertMsg ? `<div class="break-alert">${p.alertMsg}</div>` : ''}
                    </div>
                `).join('');

                let dispTarget = finalTargetBP === 'B' ? '<span class="tag-B">投 莊 (B)</span>' : finalTargetBP === 'P' ? '<span class="tag-P">投 閒 (P)</span>' : '<span class="tag-N">權重抵銷 (觀望)</span>';

                gridHtml += `<div class="analysis-card"><div class="card-header"><span class="card-title">${name} 核心引擎</span><div class="card-meta">${dispTarget}</div></div><div class="analysis-cores" style="grid-template-columns: 1fr;">${rulesHtml}</div></div>`;
                if (finalTargetBP !== 'N') reasonText += `• ${name}: 觸發 [${res.predictions.map(x=>x.name).join(', ')}]，綜合指向 ${finalTargetBP === 'B'?'莊':'閒'}。\n`;
            };

            processCore('主大路', resBR, null);
            processCore('大眼仔', resBE, { B: askData.B.bigEye, P: askData.P.bigEye });
            processCore('小路', resSM, { B: askData.B.small, P: askData.P.small });
            processCore('曱甴路', resRO, { B: askData.B.roach, P: askData.P.roach });

            document.getElementById('analysisGrid').innerHTML = `<div class="analysis-cores">${gridHtml}</div>`;

            // 更新最終決策面板
            let finalTargetEl = document.getElementById('finalTarget');
            let finalReasonEl = document.getElementById('finalReason');

            if (state.history.length < 5) {
                finalTargetEl.className = 'final-target target-N';
                finalTargetEl.innerText = '觀望 (數據不足)';
                finalReasonEl.innerText = '系統需要至少 5 局有效資料啟動 12 大邏輯權重引擎。';
            } else if (finalVotes.B === 0 && finalVotes.P === 0) {
                finalTargetEl.className = 'final-target target-N';
                finalTargetEl.innerText = '堅決觀望';
                finalReasonEl.innerText = '當前無明顯邏輯成型，或多方邏輯產生嚴重衝突，系統啟動防禦機制建議觀望。';
            } else if (finalVotes.B > finalVotes.P) {
                finalTargetEl.className = 'final-target target-B';
                finalTargetEl.innerText = '強烈推薦：莊 (Banker)';
                finalReasonEl.innerText = `莊家總權重 [${finalVotes.B}] 領先。\n` + reasonText;
            } else if (finalVotes.P > finalVotes.B) {
                finalTargetEl.className = 'final-target target-P';
                finalTargetEl.innerText = '強烈推薦：閒 (Player)';
                finalReasonEl.innerText = `閒家總權重 [${finalVotes.P}] 領先。\n` + reasonText;
            } else {
                finalTargetEl.className = 'final-target target-N';
                finalTargetEl.innerText = '觀望 (權重抵銷)';
                finalReasonEl.innerText = `莊閒總權重 [${finalVotes.B}] 呈 1:1 平手，極度不穩定，請迴避此局。`;
            }
        }
    };

    // --- 5. 對外開放的 API (Controllers) ---
    return {
        init() { UI.updateAll(); },
        record(result) {
            if (state.history.length >= state.MAX_HANDS) return alert(`已達 ${state.MAX_HANDS} 局上限！`);
            state.history.push(result);
            UI.updateAll();
        },
        undo() {
            state.history.pop();
            UI.updateAll();
        },
        clear() {
            state.history = [];
            document.getElementById("batchInput").value = "";
            UI.updateAll();
        },
        loadBatch(inputStr) {
            if (!inputStr) return;
            let cleanStr = inputStr.toUpperCase().replace(/莊/g, 'B').replace(/閒/g, 'P').replace(/和/g, 'T');
            let tokens = cleanStr.split(/,|\s|;|\|/);
            let parsed = [];
            tokens.forEach(t => {
                if (['B','P','T'].includes(t)) parsed.push(t);
                else for (let c of t) if (['B','P','T'].includes(c)) parsed.push(c);
            });
            if (parsed.length + state.history.length > state.MAX_HANDS) return alert(`匯入將超過上限！`);
            state.history = state.history.concat(parsed);
            document.getElementById("batchInput").value = "";
            UI.updateAll();
        }
    };
})();

// ============================================
// 全域函式綁定 (無縫橋接 HTML onclick 事件)
// ============================================
window.recordResult = (res) => BaccaratApp.record(res);
window.undoRecord = () => BaccaratApp.undo();
window.clearRecords = () => BaccaratApp.clear();
window.loadBatchInput = () => BaccaratApp.loadBatch(document.getElementById("batchInput").value.trim());
window.handleKeyPress = (e) => { if (e.key === 'Enter') window.loadBatchInput(); };

// 初始化系統啟動
BaccaratApp.init();
