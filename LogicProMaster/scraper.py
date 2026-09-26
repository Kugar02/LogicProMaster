import time

class MTLiveScraper:
    def __init__(self, casino_url):
        self.casino_url = casino_url
        self.is_running = False

    def start_monitoring(self):
        """啟動瀏覽器監控 (預留 Playwright / Selenium 接口)"""
        self.is_running = True
        print(f"已連結至目標賭場: {self.casino_url}")

    def get_live_scores(self):
        """讀取實時比分 (若未連接實體瀏覽器則傳回 None)"""
        if not self.is_running:
            return None
        # 可在此導入 Selenium / Playwright 解析網頁 HTML 取得莊閒和局數
        return None