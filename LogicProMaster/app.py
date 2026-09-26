@@
     if btn_cols[3].button('↩️ 撤銷', use_container_width=True):
         if st.session_state.history:
             st.session_state.history.pop()
             st.session_state.ai_targets.pop()
         st.rerun()
+
+    # ===== 新增：重置新靴按鈕 & 注碼勝率統計顯示 =====
+    if right.button("🗑️ 清空重置 (新靴)", use_container_width=True):
+        st.session_state.history = []
+        st.session_state.ai_targets = []
+        # 可選：同時重置本金與基礎注碼
+        # st.session_state.bankroll = 10000
+        # st.session_state.base_unit = 100
+        st.session_state.window, st.session_state.alpha = auto_adjust_window_alpha([])
+        st.rerun()
+
+    st.markdown('#### 📋 注碼與勝率統計')
+    winrate_display = f"{(wins/total_bets*100):.1f}%" if total_bets > 0 else "0.0%"
+    bank_with_pnl = st.session_state.bankroll + pnl
+    st.write(f"總下注次數: {total_bets} ，勝 {wins} / 負 {losses} ，勝率: {winrate_display}")
+    st.write(f"策略累計損益: ${pnl:.2f} ，含本金總資產: ${bank_with_pnl:.2f}")
+    st.write(f"最終權重 -> 莊: {final_b_pct}% ，閒: {final_p_pct}% ，可信度: {confidence_pct}%")
+    st.markdown('---')
@@
 