import json
import logging
import re
import time
import psycopg2
import scrapy
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


SCROLL_DOWN_JS_SCRIPT = """
    window.scrollBy(0,10000)
"""



class ShabSpider(scrapy.Spider):
    name = "shub_publications"
    journal_number_reg = re.compile(r'Journal Number (?P<journal_number>\d*) from (?P<publication_date>.*)')

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "https": "shab_scraper.download_handler.SeleniumDownloadHandler"
        },
        "CONCURRENT_REQUESTS": 100,
        "CONCURRENT_ITEMS": 100,
        "LOG_LEVEL": "INFO",
        "DESTINATION_FILE": "results/publications.jl"
    }
    start_url = "https://shab.ch/#!/search/publications"

    PUBLICATIONS_TYPE_PREFIXES = (
        "change",
        "new entries",
        "deletion"
    )

    @classmethod
    def update_settings(cls, settings):
        if hasattr(cls, "CONCURRENT_REQUESTS_PER_DOMAIN"):
            settings["CONCURRENT_REQUESTS_PER_DOMAIN"] = cls.CONCURRENT_REQUESTS_PER_DOMAIN
        settings.setdict(cls.custom_settings or {}, priority='spider')

    def start_requests(self):

        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--headless')
        # chrome_options.add_argument('--no-sandbox')
        driver = webdriver.Chrome(executable_path='chromedriver_linux64/chromedriver',
                                  chrome_options=chrome_options)
        # driver.set_window_size(1920, 1080)
        driver.get(self.start_url)
        time.sleep(10)
        # WebDriverWait(driver, 30).until(
        #     EC.visibility_of_element_located((By.CSS_SELECTOR, ".app-content-left")))
        eng = driver.find_element_by_link_text("EN")
        eng.click()
        time.sleep(10)
        # WebDriverWait(driver, 30).until(
        #     EC.visibility_of_element_located((By.CSS_SELECTOR,
        #                                       ".app-content-center.block-ui-active.block-ui-visible")))
        # WebDriverWait(driver, 30).until(
        #     EC.invisibility_of_element_located((By.CSS_SELECTOR,
        #                                         ".app-content-center.block-ui-active.block-ui-visible")))

        # seven_days_button = driver.find_element_by_id("last-seven-days")
        seven_days_button = driver.find_element_by_id("today")

        seven_days_button.click()
        time.sleep(10)
        # WebDriverWait(driver, 30).until(
        #     EC.visibility_of_element_located((By.CSS_SELECTOR,
        #                                       ".app-content-center.block-ui-active.block-ui-visible")))
        # WebDriverWait(driver, 30).until(
        #     EC.invisibility_of_element_located((By.CSS_SELECTOR,
        #                                         ".app-content-center.block-ui-active.block-ui-visible")))
        count_el = driver.find_element_by_css_selector("#totalItemsCount strong")
        publications_num = count_el.text
        logging.info("Total publications: %s", publications_num)

        loaded_els_num = 0
        while True:
            logging.info("Load publications")
            driver.execute_script(SCROLL_DOWN_JS_SCRIPT)
            els = driver.find_elements_by_css_selector("publication-list .list-entry .list-row a")
            els_num = len(els)
            if els_num > int(publications_num):
                logging.info("loaded last publications")
                break
            attemps = 0
            should_stop = False
            while True:
                logging.info("Waiting for new elements")
                if loaded_els_num > els_num:
                    break
                loaded_els = driver.find_elements_by_css_selector("publication-list .list-entry .list-row a")
                loaded_els_num = len(loaded_els)
                time.sleep(1)
                attemps += 1
                driver.execute_script(SCROLL_DOWN_JS_SCRIPT)
                if attemps > 30:
                    res = driver.get_screenshot_as_png()
                    with open('test.png', 'wb') as f_:
                        f_.write(res)
                    should_stop = True
                    break
            logging.info("Collected pubs: %s from %s", loaded_els_num, publications_num)
            if should_stop:
                logging.info("Session expired. Stop fetching publications links")
                break
        els = driver.find_elements_by_css_selector("publication-list .list-entry .list-row a")
        urls = []
        for publication_el in els:
            url = publication_el.get_attribute("href")
            logging.info("URL appended: %s", url)
            urls.append(url)
        logging.info("URLs collected: %s", len(urls))
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        ii = {}
        html = response.text
        soup = BeautifulSoup(html, 'lxml')

        ii['UID'] = soup.find('ul', class_='cmp-uid-list list-unstyled').find('a').text.strip()
        ii['publication_text'] = soup.find('div', class_='app-content-center').text.strip()
        items = str(soup.find_all('div', class_='field-value')[0].find_all('div')[-1]).replace('<div>', '').replace(
            '<span>', '').replace('</span>', '').replace('</div>', '').replace('\u200b', '').replace('<i>', '').replace(
            '</i>', '').strip().split(sep='<br/>')

        ii["company_name"] = items[0]
        ii["address"] = items[-2]
        ii["zip_code"] = items[-1].strip().split(sep=' ')[0]
        ii["town"] = ' '.join(items[-1].strip().split(sep=' ')[1:]).replace('\u200b', '')

        if ii["zip_code"] == '' and ii["town"] == '':
            items = str(soup.find_all('div', class_='field-value')[1].find_all('div')[-1]).replace('<div>', '').replace(
                '</div>', '').replace('\u200b', '').replace('<i>', '').replace(
                '</i>', '').replace('<span>', '').replace('</span>', '').strip().split(sep='<br/>')
            ii["address"] = items[-2]
            ii["zip_code"] = items[-1].strip().split(sep=' ')[0]
            ii["town"] = ' '.join(items[-1].strip().split(sep=' ')[1:]).replace('\u200b', '')

        ii['publication_title'] = soup.find('h3', class_='app-content-headline').text
        ii['url'] = response.url
        ii['category'] = soup.find_all('dd')[0].text.strip()
        ii['subcategory'] = soup.find_all('dd')[1].text.strip()
        ii['publication_date'] = soup.find_all('dd')[2].find('span').text.strip()
        ii['publication_number'] = soup.find(text='Publication number').parent.next_sibling.next_sibling.text
        if soup.find_all('div', class_='field-value')[-3].text.strip().startswith('Journal Number'):
            ii["journal_number"] = soup.find_all('div', class_='field-value')[-3].text.strip().split(sep=' ')[2]
            ii["journal_date"] = soup.find_all('div', class_='field-value')[-3].text.strip().split(sep=' ')[-1]
        else:
            ii["journal_number"] = 'no data'
            ii["journal_date"] = 'no data'

        # write to db
        self.open_db()
        self.cur.execute(
            """INSERT INTO Item (UID, publication_text, company_name, address, zip_code, town, journal_number, 
            journal_date, publication_title, url, category, subcategory, publication_number, publication_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (
                ii['UID'],
                ii['publication_text'],
                ii['company_name'],
                ii['address'],
                ii['zip_code'],
                ii['town'],
                ii['journal_number'],
                ii['journal_date'],
                ii['publication_title'],
                ii['url'],
                ii['category'],
                ii['subcategory'],
                ii['publication_number'],
                ii['publication_date'],
            )
        )
        self.connection.commit()
        self.close_db()

        # dt_list = response.css('publication-metadata dl dt ::text')
        # dd_list = response.css('publication-metadata dl dd ::text')
        # dt_text_list = [dt_el.extract().strip() for dt_el in dt_list if dt_el.extract().strip()]
        # dd_text_list = [dd_el.extract().strip() for dd_el in dd_list if dd_el.extract().strip()]
        # dt_text_list = dt_text_list[-len(dd_text_list):]
        # publication_info_list = zip(dt_text_list, dd_text_list)
        # for title, value in publication_info_list:
        #     title_parsed = title.lower().replace(" ", "_")
        #     if title_parsed == 'publication_date':
        #         value_parsed = value.split(" - ")[-1]
        #     elif title_parsed == 'canton':
        #         continue
        #     else:
        #         value_parsed = value
        #     ii[title_parsed] = value_parsed
        # company_uuid = response.css("company-details a ::text").extract_first() or ''
        # # ii["UID"] = company_uuid.strip()
        #
        # publication_info = response.css("publication-content div text-area-field ::text").extract()
        # company_name = ''
        # address = ''
        # zip_town = ''
        # zip_code = ''
        # town = ''
        # journal_number = ''
        # journal_date = ''
        # publication_text = ''
        # curr_publication_text = ''
        # string_num = 0
        # for publication_str in publication_info:
        #     publication_str = publication_str.strip()
        #     if not publication_str or 'c/o' in publication_str:
        #         continue
        #
        #     if string_num == 0:
        #         company_name += publication_str
        #         string_num += 1
        #     elif publication_str.startswith('('):
        #         company_name += publication_str
        #     elif string_num == 1:
        #         address += publication_str
        #         string_num += 1
        #     elif string_num == 2:
        #         zip_town += publication_str
        #         zip_town_splited = zip_town.split(' ')
        #         if len(zip_town_splited) > 1:
        #             zip_code += zip_town_splited[0].strip()
        #             town += ' '.join(zip_town_splited[1:]).strip()
        #         elif len(zip_town_splited) == 1:
        #             town += zip_town_splited[0].strip()
        #         string_num += 1
        #     if publication_str.startswith('Journal Number'):
        #         journal_num = self.journal_number_reg.search(publication_str)
        #         if journal_num:
        #             journal_number = journal_num.group("journal_number")
        #             journal_date = journal_num.group("publication_date")
        #         publication_text = curr_publication_text
        #     curr_publication_text = publication_str
        # ii["publication_text"] = publication_text
        # ii["company_name"] = company_name
        # ii["address"] = address
        # ii["zip_code"] = zip_code
        # ii["town"] = town
        # ii["journal_number"] = journal_number
        # ii["journal_date"] = journal_date
        #
        # publication_title = response.css("h3.app-content-headline ::text").extract_first()
        # if publication_title:
        #     for prefix in self.PUBLICATIONS_TYPE_PREFIXES:
        #         if publication_title.lower().strip().startswith(prefix):
        #             publication_title = publication_title.strip()[len(prefix):].strip()
        # ii["publication_title"] = publication_title or ''
        # ii["url"] = response.url

        yield ii

    def open_db(self):
        """open the database"""
        hostname = '127.0.0.1'
        username = 'parsing_admin'
        password = 'parsing_adminparsing_admin'
        database = 'parsing'
        port = "5444"
        self.connection = psycopg2.connect(  # noqa
            host=hostname,
            user=username,
            password=password,
            dbname=database,
            port=port)
        self.cur = self.connection.cursor()  # noqa

    def close_db(self):
        """close the database"""
        self.cur.close()
        self.connection.close()
