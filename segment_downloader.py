import os
import time
from config import Config


class SegmentDownloader:
    def __init__(self, driver):
        self.driver = driver

    def download(self, segments):
        print("\nСкачиваем сегменты через браузер...")
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

        for url in segments:
            print("Downloading:", url)
            self.driver.get(url)
            time.sleep(2)

        print("Все сегменты скачаны")

    def verify_segments(self, expected_count):
        actual_count = len([f for f in os.listdir(Config.OUTPUT_DIR) if f.endswith(".ts")])
        if actual_count != expected_count:
            print(f"ВНИМАНИЕ: Ожидалось {expected_count} сегментов, найдено {actual_count}")
            return False
        print(f"Целостность проверена: {actual_count} сегментов")
        return True