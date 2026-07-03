import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import Config


class BrowserManager:
    def __init__(self):
        self.driver = None

    def setup(self):
        options = Options()
        options.binary_location = Config.CHROME_PATH
        prefs = {
            "download.default_directory": os.path.abspath(Config.OUTPUT_DIR),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return self.driver

    def open_vpn_page(self):
        self.driver.get(
            "https://chromewebstore.google.com/detail/%D0%B1%D0%B5%D1%81%D0%BF%D0%BB%D0%B0%D1%82%D0%BD%D1%8B%D0%B9-vpn-proxy-vpnl/lneaocagcijjdpkcabeanfpdbmapcjjg?hl=ru"
        )

    def open_auth_page(self):
        self.driver.switch_to.new_window("tab")
        self.driver.get("https://anthropic.skilljar.com/")

    def wait_for_auth(self):
        input("ВКЛЮЧИТЕ ВПН И АВТОРИЗИРУЙТЕСЬ НА НУЖНОМ ВАМ САЙТЕ. ENTER для продолжения")

    def open_video_page(self, url):
        self.driver.switch_to.new_window("tab")
        self.driver.get(url)

    def wait_for_video_buffer(self):
        print("\nДай видео полностью прогрузить сегменты.")
        input("Запусти видео, подожди немного и нажми ENTER\n")