import shutil
from config import Config
from page_parser import PageParser
from m3u8_parser import M3U8Parser
from segment_downloader import SegmentDownloader
from video_builder import VideoBuilder
from video_translator import VideoTranslator


class DownloadPipeline:
    def __init__(self, driver):
        self.driver = driver
        self.page_parser = PageParser(driver)
        self.m3u8_parser = M3U8Parser(driver)
        self.segment_downloader = SegmentDownloader(driver)
        self.video_builder = VideoBuilder()
        self.video_translator = VideoTranslator()

    def process(self, url):
        self.driver.get(url)
        print("\nВключи VPN если нужно.")
        self.driver.execute_script("window.close()")

        title = self.page_parser.parse_title()
        print(f"Название урока: {title}")

        self.driver.switch_to.window(self.driver.window_handles[-1])
        input("Дай видео полностью прогрузить сегменты. Запусти видео, подожди немного и нажми ENTER\n")

        urls = self.m3u8_parser.collect_ts_urls()
        best_segments = self.m3u8_parser.select_best_segments(urls)

        self._clean_output_dir()
        self.segment_downloader.download(best_segments)
        self.segment_downloader.verify_segments(self.m3u8_parser.total_segments)

        original_file = f"{title}.mp4"
        self.video_builder.create_list_file()
        self.video_builder.merge_video(original_file)

        translated_file = self.video_translator.translate(original_file)

        print(f"\nОригинал: {original_file}")
        print(f"Перевод: {translated_file}")

    def _clean_output_dir(self):
        shutil.rmtree(Config.OUTPUT_DIR, ignore_errors=True)