from pipeline import DownloadPipeline
from browser_manager import BrowserManager


class ConsoleMenu:
    def __init__(self, driver, browser_manager):
        self.driver = driver
        self.browser_manager = browser_manager
        self.pipeline = DownloadPipeline(driver)

    def run(self):
        while True:
            print("\n==============================")
            print(" VIDEO DOWNLOADER ")
            print("==============================\n")
            print("1. Скачать видео с одной страницы")
            print("2. Скачать список страниц")
            print("3. Выйти из аккаунта")
            print("4. Выход\n")

            choice = input("Выбери пункт: ")

            if choice == "1":
                self._run_single_page()
            elif choice == "2":
                self._run_list_pages()
            elif choice == "3":
                self._logout()
            elif choice == "4":
                print("\nВыход.")
                break
            else:
                print("\nНеверный пункт\n")

    def _run_single_page(self):
        print("\n=== СКАЧИВАНИЕ ОДНОЙ СТРАНИЦЫ ===\n")
        url = input("Вставь ссылку на страницу с видео:\n> ")
        self.pipeline.process(url)

    def _run_list_pages(self):
        print("\n=== СКАЧИВАНИЕ НЕСКОЛЬКИХ СТРАНИЦ ===\n")
        urls_input = input("Вставь ссылки с видео (каждая с новой строки или через пробел):\n> ")
        urls = [url.strip() for url in urls_input.replace(",", " ").split() if url.strip()]

        if not urls:
            print("Ссылки не найдены")
            return

        print(f"\nНайдено ссылок: {len(urls)}\n")

        for i, url in enumerate(urls, 1):
            print(f"\n===== Видео {i}/{len(urls)} =====")
            print(url)
            self.pipeline.process(url)

    def _logout(self):
        print("\n=== ВЫХОД ИЗ АККАУНТА ===\n")
        confirm = input("Вы уверены? Все сохраненные куки и пароли будут удалены. (y/n): ")
        if confirm.lower() == 'y':
            self.browser_manager.clear_profile()
            print("Перезапустите программу для применения изменений.")
        else:
            print("Отменено.")