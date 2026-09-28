import requests
import json
from datetime import datetime
import streamlit as st

# 將剛才複製的 Apps Script Web app URL 放在 Secrets 或直接貼在這裡
GAS_WEBHOOK_URL = st.secrets.get("WEBHOOK_URL", "貼上你複製的_WEB_APP_URL")

def upload_shoe_to_kugar(shoe_history, session_stats=None, shoe_id=None):
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
            GAS_WEBHOOK_URL,
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
