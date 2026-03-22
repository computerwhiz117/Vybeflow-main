import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

class FeedPageLinksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        cls.driver = webdriver.Chrome(options=chrome_options)
        # Update this URL to your local server if needed
        cls.base_url = 'http://localhost:5000/feed'

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_all_links(self):
        driver = self.driver
        driver.get(self.base_url)
        time.sleep(2)  # Wait for page to load
        links = driver.find_elements(By.TAG_NAME, 'a')
        hrefs = set()
        for link in links:
            href = link.get_attribute('href')
            if href and not href.startswith('javascript:'):
                hrefs.add(href)
        failed_links = []
        for href in hrefs:
            try:
                driver.get(href)
                time.sleep(1)
                # Check for HTTP errors by looking for error in page title or body
                if '404' in driver.title or 'Not Found' in driver.page_source:
                    failed_links.append((href, '404 Not Found'))
                elif '500' in driver.title or 'Internal Server Error' in driver.page_source:
                    failed_links.append((href, '500 Internal Server Error'))
            except Exception as e:
                failed_links.append((href, str(e)))
        self.assertEqual(len(failed_links), 0, f"Broken links found: {failed_links}")

if __name__ == '__main__':
    unittest.main()
