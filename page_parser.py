import re
from selenium.webdriver.common.by import By


class PageParser:
    def __init__(self, driver):
        self.driver = driver

    def parse_title(self):
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, "#lesson-main-inner h2")
            title = element.text.strip()
        except:
            title = "video"
        return self._sanitize_filename(title)

    def _sanitize_filename(self, filename):
        invalid_chars = r'[\\/:*?"<>|]'
        return re.sub(invalid_chars, '_', filename)