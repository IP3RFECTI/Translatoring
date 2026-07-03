import json
import re
import time
from urllib.parse import urljoin
from collections import defaultdict
import requests
from config import Config


class M3U8Parser:
    def __init__(self, driver):
        self.driver = driver
        self.total_segments = None

    def _get_text(self, url):
        return requests.get(url, headers=Config.HEADERS).text

    def get_total_segments(self, master_url):
        try:
            master = self._get_text(master_url)
            playlist_url = None
            for line in master.split("\n"):
                if line.endswith(".m3u8"):
                    playlist_url = urljoin(master_url, line)
            playlist = self._get_text(playlist_url)
            segments = [line for line in playlist.split("\n") if line.endswith(".ts")]
            self.total_segments = len(segments)
            return self.total_segments
        except:
            return None

    def collect_ts_urls(self):
        print("\nСобираем ts сегменты...")
        urls = set()
        segment_numbers = set()
        playlist_m3u8 = None
        start = time.time()

        while True:
            try:
                logs = self.driver.get_log("performance")
            except:
                logs = []

            for entry in logs:
                try:
                    message = json.loads(entry["message"])["message"]
                except:
                    continue

                if message["method"] == "Network.responseReceived":
                    url = message["params"]["response"]["url"]

                    if ".m3u8" in url and not playlist_m3u8:
                        playlist_m3u8 = url
                        print("\nНайден m3u8:", playlist_m3u8)
                        self.get_total_segments(playlist_m3u8)
                        print("Segments:", self.total_segments)

                    if ".ts" in url:
                        num_match = re.search(r'-(\d+)\.ts', url)
                        if not num_match:
                            continue
                        num = int(num_match.group(1))
                        if url not in urls:
                            urls.add(url)
                            segment_numbers.add(num)
                            print("Segment:", num)

            if self.total_segments:
                missing = [i for i in range(1, self.total_segments + 1) if i not in segment_numbers]
                if not missing:
                    print("\nВсе сегменты найдены")
                    return sorted(list(urls))

            if not self.total_segments and len(segment_numbers) > 50:
                print("\nПлейлист не найден, возвращаем сегменты")
                return sorted(list(urls))

            if time.time() - start > 600:
                print("\nТаймаут ожидания")
                if self.total_segments:
                    print("Отсутствуют сегменты:", missing)
                break

            time.sleep(1)

        return sorted(list(urls))

    def select_best_segments(self, urls):
        print("\nВыбираем лучшее качество сегментов...")
        segments_by_number = defaultdict(list)

        for url in urls:
            num_match = re.search(r'-(\d+)\.ts', url)
            if not num_match:
                continue
            num = int(num_match.group(1))

            quality_match = re.search(r'=(\d+)-\d+\.ts', url)
            if not quality_match:
                continue
            quality = int(quality_match.group(1))

            segments_by_number[num].append((quality, url))

        if not segments_by_number:
            print("Не удалось определить качество")
            return sorted(urls)

        result = []
        for num in sorted(segments_by_number.keys()):
            best = max(segments_by_number[num], key=lambda x: x[0])
            result.append(best[1])
            print(f"Segment {num} -> quality {best[0]}")

        return result