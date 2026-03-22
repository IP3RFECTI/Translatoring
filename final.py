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

import warnings

warnings.filterwarnings("ignore")

TOKEN = "" # Введите свой яндекс токен

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
    try:

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
    except:
        print("\nПроверяем количество сегментов")

        master = get_text(master_url)

        playlist_url = None

        # ищем playlist
        for line in master.splitlines():
            if ".m3u8" in line and not line.startswith("#"):
                playlist_url = urljoin(master_url, line)

        print("Playlist:", playlist_url)

        playlist = get_text(playlist_url)

        segments = []

        for line in playlist.splitlines():

            if line.endswith(".ts"):
                segments.append(urljoin(playlist_url, line))

        print("Segments:", len(segments))

        return segments
    finally: print(f'Сегменты: {segments}. Если тут ничего нет, то значит ниче не нашлось.')

def collect_ts_urls(driver):

    print("\nСобираем ts сегменты...")

    urls = set()
    segment_numbers = set()

    playlist_m3u8 = None
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

                # ---- ловим m3u8 ----
                if ".m3u8" in url and not playlist_m3u8:

                    playlist_m3u8 = url

                    print("\nНайден m3u8:")
                    print(playlist_m3u8)

                    try:
                        total_segments = get_total_segments(playlist_m3u8)
                        print("Segments:", total_segments)
                    except:
                        total_segments = None

                # ---- ts сегменты ----
                if ".ts" in url:

                    num_match = re.search(r'-(\d+)\.ts', url)

                    if not num_match:
                        continue

                    num = int(num_match.group(1))

                    if url not in urls:
                        urls.add(url)
                        segment_numbers.add(num)

                        print("Segment:", num)

        # ---- проверяем что есть все номера ----
        if total_segments:

            missing = [
                i for i in range(1, total_segments + 1)
                if i not in segment_numbers
            ]

            if not missing:

                print("\nВсе сегменты найдены")
                return sorted(list(urls))

        # ---- fallback если m3u8 не нашли ----
        if not total_segments and len(segment_numbers) > 50:

            print("\nПлейлист не найден, возвращаем сегменты")
            return sorted(list(urls))

        if time.time() - start > 600:

            print("\nТаймаут ожидания")

            if total_segments:
                print("Отсутствуют сегменты:", missing)

            break

        time.sleep(1)

    return sorted(list(urls))


# ---------- выбрать лучшее качество ----------
import re
from collections import defaultdict

def select_best_segments(urls):

    print("\nВыбираем лучшее качество сегментов...")

    segments_by_quality = defaultdict(dict)
    all_sym_ids = set()

    # 1. Собираем сегменты и все уникальные quality-id
    for url in urls:

        num_match = re.search(r'-(\d+)\.ts', url)
        if not num_match:
            continue

        num = int(num_match.group(1))

        sym_match = re.search(r'SYM1lOWb=(\d+)', url)
        if not sym_match:
            continue

        sym_id = int(sym_match.group(1))
        all_sym_ids.add(sym_id)

        segments_by_quality[sym_id][num] = url

    if not segments_by_quality:
        print("⚠ Не удалось определить качество")
        return sorted(urls)

    # 2. Сортируем качества по убыванию (чем больше — тем лучше)
    sorted_sym_ids = sorted(all_sym_ids, reverse=True)

    # 3. Назначаем им "человеческие" качества
    quality_labels = [1080, 720, 480, 240]
    quality_map_dynamic = {
        sym_id: quality_labels[i] if i < len(quality_labels) else 0
        for i, sym_id in enumerate(sorted_sym_ids)
    }

    print("Определённые качества:", quality_map_dynamic)

    # 4. Сколько максимум сегментов
    max_segments = max(
        max(q.keys()) for q in segments_by_quality.values()
    )

    result = []

    # 5. Выбираем лучший сегмент для каждого номера
    for i in range(1, max_segments + 1):

        chosen = None
        chosen_q = None

        for sym_id in sorted_sym_ids:
            if i in segments_by_quality[sym_id]:
                chosen = segments_by_quality[sym_id][i]
                chosen_q = quality_map_dynamic[sym_id]
                break

        if chosen:
            result.append(chosen)
            print(f"Segment {i} -> {chosen_q}p")
        else:
            print(f"⚠ Segment {i} missing completely")

    return result

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

    # функция извлечения номера сегмента
    def segment_number(name):
        match = re.search(r'-(\d+)\.ts$', name)
        return int(match.group(1)) if match else -1

    # сортировка по номеру сегмента
    files.sort(key=segment_number)

    with open("list.txt", "w", encoding="utf-8") as f:

        for file in files:

            path = os.path.join(OUTPUT_DIR, file).replace("\\", "/")

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
def main(driver, my_url):

    driver.switch_to.new_window("tab")

    driver.get(
        f'{my_url}'
    )

    # driver.get(
    #     "https://learn.deeplearning.ai/courses/build-with-andrew/lesson/a45t1o/creating-an-app-with-ai"
    # )

    print("\nВключи VPN если нужно.")

    wait_for_video_buffer()

    urls = collect_ts_urls(driver)

    best_segments = select_best_segments(urls)

    download_segments(driver, best_segments)

    create_list_file()

    merge_video()

    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    print("Папка segments удалена")


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


def replace_audio(output_name):

    print("Replacing audio track...")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", LOCAL_FILE,
        "-i", AUDIO_FILE,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_name
    ], check=True)

    print("✅ New video created:", output_name)

def cleanup_files():

    files = [
        "video_1.mp4",
        "translation.mp3"
    ]

    for file in files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Удален файл: {file}")

def delete_file():

    headers = {"Authorization": f"OAuth {TOKEN}"}

    print("Deleting file from Yandex Disk...")

    r = requests.delete(
        f"{BASE_URL}/resources",
        headers=headers,
        params={
            "path": DISK_FILE,
            "permanently": "true"
        }
    )

    r.raise_for_status()

    print("✅ File deleted from Yandex Disk")

def translation_pipeline():

    output_name = get_next_output_name()

    try:
        upload_file()

        publish_file()

        time.sleep(5)

        public_url = get_public_url()

        audio_url = run_vot(public_url)

        download_audio(audio_url)

        replace_audio(output_name)

        print("\n🎉 DONE")
    finally:
        try:
            delete_file()
        except:
            pass

        cleanup_files()

def get_next_output_name():

    i = 1

    while True:

        name = f"video_{i}_translated.mp4"

        if not os.path.exists(name):
            return name

        i += 1

def run_single_page(driver):

    print("\n=== СКАЧИВАНИЕ ОДНОЙ СТРАНИЦЫ ===\n")

    my_url = input("Вставь ссылку на страницу с видео:\n> ")

    main(driver, my_url)

    translation_pipeline()


def run_list_pages():

    print("\n=== СКАЧИВАНИЕ НЕСКОЛЬКИХ СТРАНИЦ ===\n")

    my_urls = input("Вставь ссылки с видео (каждая с новой строки или через пробел):\n> ")

    # разбиваем строку на список ссылок
    urls = [url.strip() for url in my_urls.replace(",", " ").split() if url.strip()]

    if not urls:
        print("❌ Ссылки не найдены")
        return

    print(f"\nНайдено ссылок: {len(urls)}\n")

    for i, url in enumerate(urls, 1):
        print(f"\n===== Видео {i}/{len(urls)} =====")
        print(url)

        main(driver, url)
        translation_pipeline()


def run_playlist():
    """
    Пункт 3:
    AI агент или парсер курса
    (пока не реализован)
    """

    print("\nФункция пока не реализована\n")


# =====================================================
# КОНСОЛЬНОЕ МЕНЮ
# =====================================================
def config():
    print("\n==============================")
    print(" CONFIGURATION... ")
    print("==============================\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    driver = setup_browser()

    driver.get(
        "https://chromewebstore.google.com/detail/%D0%B1%D0%B5%D1%81%D0%BF%D0%BB%D0%B0%D1%82%D0%BD%D1%8B%D0%B9-vpn-proxy-vpnl/lneaocagcijjdpkcabeanfpdbmapcjjg?hl=ru"
    )

    driver.switch_to.new_window("tab")

    driver.get(
        'https://anthropic.skilljar.com/'
    )

    input("ВКЛЮЧИТЕ ВПН И АВТОРИЗИРУЙТЕСЬ НА НУЖНОМ ВАМ САЙТЕ. ENTER для продолжения")

    return driver

def console_app(driver):

    while True:

        print("\n==============================")
        print(" VIDEO DOWNLOADER ")
        print("==============================\n")

        print("1. Скачать видео с одной страницы")
        print("2. Скачать список страниц")
        print("3. Скачать курс целиком")
        print("4. Выход\n")

        choice = input("Выбери пункт: ")

        if choice == "1":
            run_single_page(driver)

        elif choice == "2":
            run_list_pages()

        elif choice == "3":
            run_playlist()

        elif choice == "4":

            print("\nВыход.")

            break

        else:

            print("\nНеверный пункт\n")


# =====================================================
# ЗАПУСК
# =====================================================

if __name__ == "__main__":
    driver = config()
    console_app(driver)

