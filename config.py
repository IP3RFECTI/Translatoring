import os


class Config:
    TOKEN = "ВСТАВИТЬ СВОЙ ТОКЕН СЮДА"
    OUTPUT_DIR = "segments"
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    BROWSER_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_profile")
    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://learn.deeplearning.ai/",
        "Origin": "https://learn.deeplearning.ai"
    }
    BASE_URL = "https://cloud-api.yandex.net/v1/disk"