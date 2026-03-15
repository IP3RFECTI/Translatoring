import os
import json
import time
import subprocess
import shutil
import re
from urllib.parse import urljoin

import requests

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

TOKEN = "yandex token here"
OUTPUT_DIR = "segments"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://learn.deeplearning.ai/",
    "Origin": "https://learn.deeplearning.ai"
}


# ---------- генерация имени mp4 ----------
def generate_output_name():

    i = 1
    while True:

        name = f"video_{i}.mp4"

        if not os.path.exists(name):
            return name

        i += 1


# ---------- запуск браузера ----------
def setup_browser():

    options = Options()
    options.binary_location = CHROME_PATH

    prefs = {
        "download.default_directory": os.path.abspath(OUTPUT_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }

    options.add_experimental_option("prefs", prefs)

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


# ---------- получить текст ----------
def get_text(url):
    return requests.get(url, headers=headers).text


# ---------- узнать количество сегментов ----------
def get_total_segments(master_url):

    print("\nПроверяем количество сегментов через master.m3u8")

    master = get_text(master_url)

    playlist_url = None

    for line in master.split("\n"):
        if line.endswith(".m3u8"):
            playlist_url = urljoin(master_url, line)

    print("Playlist:", playlist_url)

    playlist = get_text(playlist_url)

    segments = []

    for line in playlist.split("\n"):
        if line.endswith(".ts"):
            segments.append(urljoin(playlist_url, line))

    print("Segments:", len(segments))

    return len(segments)


# ---------- сбор ts ----------
def collect_ts_urls(driver):

    print("\nСобираем ts сегменты...")

    urls = set()
    master_m3u8 = None
    total_segments = None

    start = time.time()

    while True:

        try:
            logs = driver.get_log("performance")
        except:
            logs = []

        for entry in logs:

            try:
                message = json.loads(entry["message"])["message"]
            except:
                continue

            if message["method"] == "Network.responseReceived":

                url = message["params"]["response"]["url"]

                if ".m3u8" in url and "master" in url and not master_m3u8:

                    master_m3u8 = url

                    print("\nНайден master m3u8:")
                    print(master_m3u8)

                    total_segments = get_total_segments(master_m3u8)

                if ".ts" in url:

                    if url not in urls:
                        urls.add(url)
                        print("Segment:", len(urls))

        if total_segments and len(urls) >= total_segments:

            print("\nВсе сегменты найдены")
            return sorted(list(urls))

        if time.time() - start > 600:
            print("\nТаймаут ожидания")
            break

        time.sleep(1)

    return sorted(list(urls))


# ---------- выбрать лучшее качество ----------
def select_best_segments(urls):

    print("\nВыбираем лучшее качество сегментов...")

    best = {}

    for url in urls:

        num_match = re.search(r'_(\d+)\.ts', url)
        if not num_match:
            continue

        num = int(num_match.group(1))

        q_match = re.search(r'/video/(\d+)/', url)
        quality = int(q_match.group(1)) if q_match else 0

        if num not in best:
            best[num] = (quality, url)
        else:
            if quality > best[num][0]:
                best[num] = (quality, url)

    expected = max(best.keys())

    missing = [i for i in range(1, expected + 1) if i not in best]

    if missing:
        print("⚠ Пропущенные сегменты:", missing)

    ordered = [best[i][1] for i in sorted(best.keys())]

    print("\nВыбранные сегменты:")
    for i in sorted(best.keys()):
        print(f"Segment {i} -> {best[i][0]}p")

    return ordered


# ---------- ожидание ----------
def wait_for_video_buffer():

    print("\nДай видео полностью прогрузить сегменты.")
    input("Запусти видео, подожди немного и нажми ENTER\n")


# ---------- скачивание ----------
def download_segments(driver, segments):

    print("\nСкачиваем сегменты через браузер...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for url in segments:

        print("Downloading:", url)

        driver.get(url)

        time.sleep(2)

    print("Все сегменты скачаны")


# ---------- list.txt ----------
def create_list_file():

    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".ts")]

    files.sort()

    with open("list.txt", "w", encoding="utf-8") as f:

        for file in files:

            path = os.path.join(OUTPUT_DIR, file)

            f.write(f"file '{path}'\n")

    print("list.txt создан")


# ---------- склейка ----------
def merge_video():

    output_file = generate_output_name()

    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", "list.txt",
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output_file
    ]

    subprocess.run(cmd)

    print("Готово:", output_file)


# ---------- основной скрипт скачивания ----------
def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    driver = setup_browser()

    driver.get(
        "https://chromewebstore.google.com/detail/%D0%B1%D0%B5%D1%81%D0%BF%D0%BB%D0%B0%D1%82%D0%BD%D1%8B%D0%B9-vpn-proxy-vpnl/lneaocagcijjdpkcabeanfpdbmapcjjg?hl=ru"
    )

    driver.switch_to.new_window("tab")

    driver.get(
        "https://learn.deeplearning.ai/courses/build-with-andrew/lesson/a45t1o/creating-an-app-with-ai"
    )

    print("\nВключи VPN если нужно.")

    wait_for_video_buffer()

    urls = collect_ts_urls(driver)

    best_segments = select_best_segments(urls)

    download_segments(driver, best_segments)

    create_list_file()

    merge_video()

    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    print("Папка segments удалена")

    driver.quit()


# =====================================================
# ВТОРОЙ СКРИПТ (ПЕРЕВОД)
# =====================================================



LOCAL_FILE = "video_1.mp4"
DISK_FILE = "app:/video_1.mp4"

BASE_URL = "https://cloud-api.yandex.net/v1/disk"

AUDIO_FILE = "translation.mp3"
OUTPUT_VIDEO = "video_1_translated.mp4"


def upload_file():

    headers = {"Authorization": f"OAuth {TOKEN}"}

    print("Getting upload URL...")

    r = requests.get(
        f"{BASE_URL}/resources/upload",
        headers=headers,
        params={"path": DISK_FILE, "overwrite": "true"}
    )

    r.raise_for_status()

    upload_url = r.json()["href"]

    print("Uploading video...")

    with open(LOCAL_FILE, "rb") as f:
        requests.put(upload_url, data=f).raise_for_status()

    print("✅ Upload complete")


def publish_file():

    headers = {"Authorization": f"OAuth {TOKEN}"}

    requests.put(
        f"{BASE_URL}/resources/publish",
        headers=headers,
        params={"path": DISK_FILE}
    ).raise_for_status()

    print("✅ File published")


def get_public_url():

    headers = {"Authorization": f"OAuth {TOKEN}"}

    r = requests.get(
        f"{BASE_URL}/resources",
        headers=headers,
        params={"path": DISK_FILE}
    )

    r.raise_for_status()

    url = r.json()["public_url"]

    print("Public URL:", url)

    return url


def run_vot(url):

    print("Running vot-cli...")

    cmd = f'vot-cli {url}'

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    print(output)

    match = re.search(r'https://[^\s"]+\.mp3[^\s"]*', output)

    if not match:
        raise Exception("Audio link not found")

    audio_url = match.group(0)

    print("Audio URL:", audio_url)

    return audio_url


def download_audio(audio_url):

    print("Downloading translated audio...")

    r = requests.get(audio_url, stream=True)

    with open(AUDIO_FILE, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    print("✅ Audio downloaded")


def replace_audio():

    print("Replacing audio track...")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", LOCAL_FILE,
        "-i", AUDIO_FILE,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        OUTPUT_VIDEO
    ], check=True)

    print("✅ New video created:", OUTPUT_VIDEO)

def cleanup_files():

    files = [
        "video_1.mp4",
        "translation.mp3"
    ]

    for file in files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Удален файл: {file}")

def translation_pipeline():

    upload_file()

    publish_file()

    time.sleep(5)

    public_url = get_public_url()

    audio_url = run_vot(public_url)

    download_audio(audio_url)

    replace_audio()

    print("\n🎉 DONE")


# =====================================================
# ЗАПУСК
# =====================================================

if __name__ == "__main__":

    main()

    translation_pipeline()

    cleanup_files()