# encoding: utf-8
from __future__ import unicode_literals

import logging

from pydispatch import dispatcher
from scrapy import signals
from scrapy.http import HtmlResponse
from scrapy.signalmanager import SignalManager
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import _find_element
from selenium.webdriver.support.wait import WebDriverWait
from six.moves import queue
from twisted.internet import defer, threads
from twisted.python.failure import Failure
from selenium.webdriver.support import expected_conditions as EC

REMOVE_OVERLAY_JS_SCRIPT = """
let res = document.getElementsByClassName("block-ui-container");
if (res.length > 0){
    res[0].remove();
}
"""


class text_is_not_presented_in_element(object):
    """ An expectation for checking if the given text is present in the
    specified element.
    locator, text
    """
    def __init__(self, locator, text_):
        self.locator = locator
        self.text = text_

    def __call__(self, driver):
        try:
            element_text = _find_element(driver, self.locator).text
            return self.text not in element_text
        except StaleElementReferenceException:
            return False


class SeleniumDownloadHandler(object):

    def __init__(self, settings):
        self.options = settings.get('SELENIUM_OPTIONS', {})
        self.domain_concurrency = settings.getint('CONCURRENT_REQUESTS_PER_DOMAIN')
        self.ip_concurrency = settings.getint('CONCURRENT_REQUESTS_PER_IP')

        max_run = self.ip_concurrency if self.ip_concurrency else self.domain_concurrency
        logging.info("Download workers: %s", max_run)
        self.sem = defer.DeferredSemaphore(max_run)
        self.queue = queue.LifoQueue(max_run)

        SignalManager(dispatcher.Any).connect(self._close, signal=signals.spider_closed)

    def download_request(self, request, spider):
        return self.sem.run(self._wait_request, request, spider)

    def _wait_request(self, request, spider):
        try:
            driver = self.queue.get_nowait()
        except queue.Empty:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            driver = webdriver.Chrome(executable_path='chromedriver_linux64/chromedriver',
                                      chrome_options=chrome_options)
            # driver = webdriver.PhantomJS(**self.options)
            # driver.set_window_size(1920, 1080)
            # driver = webdriver.Chrome(chrome_options = request.meta.get('chrome_options'))
        escaped_url = request.url
        url = escaped_url.replace('?_escaped_fragment_=', '#!')
        logging.info("Start processing url: %s", url)
        try:
            pub_header = driver.find_element_by_css_selector("h3.app-content-headline").text
        except:
            pub_header = ''
        dfd = threads.deferToThread(driver.get, url)
        dfd.addCallback(self._response, driver, spider, pub_header)
        return dfd

    def _response(self, _, driver, spider, previous_pub_header):
        try:
            if previous_pub_header:
                WebDriverWait(driver, 30).until(
                    text_is_not_presented_in_element((By.CSS_SELECTOR, "h3.app-content-headline"), previous_pub_header))

            WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "publication-content")))
        except:
            logging.exception('Failed to fetch publication content. URL: %s', driver.current_url)
            driver.close()
            return defer.fail(Failure())
        driver.execute_script(REMOVE_OVERLAY_JS_SCRIPT)
        eng = driver.find_element_by_link_text("EN")
        eng.click()

        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR,
                                                ".app-content-center.block-ui-active.block-ui-visible")))
        url = driver.current_url
        body = str.encode(driver.page_source)
        resp = HtmlResponse(url, body=body, encoding='utf-8')

        response_failed = getattr(spider, "response_failed", None)
        if response_failed and callable(response_failed) and response_failed(resp, driver):
            driver.close()
            return defer.fail(Failure())
        else:
            self.queue.put(driver)
            return defer.succeed(resp)

    def _close(self):
        while not self.queue.empty():
            driver = self.queue.get_nowait()
            driver.close()


# chrome_options = webdriver.ChromeOptions()
# chrome_options.add_argument('--headless')
# chrome_options.add_argument('--no-sandbox')
# driver = webdriver.Chrome(executable_path='chromedriver_linux64/chromedriver',
#                           chrome_options=chrome_options)
# start_url = "https://shab.ch/#!/search/publications/detail/6b9b3168-c1c8-4562-b559-86fd2ec4af9b"
# st_url = "https://shab.ch/#!/search/publications/detail/4c950f70-0d24-4a52-b127-e53f007092cb"
# driver.get(start_url)
# WebDriverWait(driver, 30).until(
#                 EC.visibility_of_element_located((By.CSS_SELECTOR, "publication-content")))
# pub_header = driver.find_element_by_css_selector("h3.app-content-headline").text
# print(pub_header)
# body = str.encode(driver.page_source)
# driver.get(st_url)
# WebDriverWait(driver, 30).until(
#                 text_is_not_presents_in_element((By.CSS_SELECTOR, "h3.app-content-headline"), pub_header))
# print(driver.current_url)
# body1 = str.encode(driver.page_source)
