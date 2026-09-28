import requests
import json
from datetime import datetime
import streamlit as st

def upload_shoe_to_kugar(shoe_history, session_stats=None, shoe_id=None):
    # 從 Streamlit Secrets 讀取你設置好的 Web App 網址
    gas_url = st.secrets.get("WEBHOOK_URL")
    if not gas_url:
        return False, "Streamlit Secrets 中未設定 WEBHOOK_URL！"

    if not shoe_history:
        return False, "牌靴數據為空，未執行備份。"

    if shoe_id is None:
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        shoe_id = f"shoe_{now_str}"

    payload = {
        "shoe_id": shoe_id,
        "timestamp": datetime.now().isoformat(),
        "total_hands": len(shoe_history),
        "history_sequence": shoe_history,
        "counts": {
            "B": shoe_history.count('B'),
            "P": shoe_history.count('P'),
            "T": shoe_history.count('T')
        },
        "session_stats": session_stats or {}
    }

    try:
        response = requests.post(
            gas_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        res_data = response.json()
        if res_data.get("status") == "success":
            return True, res_data.get("file_url")
        else:
            return False, f"上傳失敗: {res_data.get('message')}"
    except Exception as e:
        return False, f"網路傳輸錯誤: {str(e)}"
