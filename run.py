#!venv/bin/python
import argparse
import json
import logging

from scrapy.utils.python import to_bytes
from scrapy.utils.serialize import ScrapyJSONEncoder
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from shab_scraper.spiders.shab_publication_spider import ShabSpider
from scrapy.utils.project import get_project_settings


configure_logging()
runner = CrawlerRunner(settings=get_project_settings())


@defer.inlineCallbacks
def crawl(download_workers):
    ShabSpider.CONCURRENT_REQUESTS_PER_DOMAIN = download_workers
    yield runner.crawl(ShabSpider)
    reactor.stop()


def run(output_path, download_workers):
    crawl(download_workers)
    reactor.run()  # the script will block here until the last crawl call is finished
    encoder = ScrapyJSONEncoder()
    with open("results/publications.jl", "rb+") as publications_info_file:
        with open(output_path, "wb+") as output_file:
            output_file.write(b"[")
            first = True
            while True:
                line = publications_info_file.readline()
                if not line:
                    break
                if first:
                    output_file.write(b"\n")
                    first = False
                else:
                    output_file.write(b",\n")
                company_info_data = json.loads(line)
                data = encoder.encode(company_info_data)
                output_file.write(to_bytes(data))
            output_file.write(b"\n]\n")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(message)s")
    parser = argparse.ArgumentParser(description='Collect Publication Info')
    parser.add_argument("--download-workers", type=int, required=False, default=40,
                        help="Number of download workers")
    parser.add_argument("--output-path", required=True, help="Path to store result")

    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args.output_path, args.download_workers)
