# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
from datetime import datetime

from scrapy.exceptions import DropItem
from scrapy.exporters import JsonLinesItemExporter


class ZefixScraperPipeline(object):

    def __init__(self):
        self.items_exporter = None
        self.processed_uids = set()

    def open_spider(self, spider):
        destination_file = spider.settings.get("DESTINATION_FILE")
        destination_dir = os.path.dirname(destination_file)
        os.makedirs(destination_dir, exist_ok=True)
        if os.path.exists(destination_file):
            os.replace(destination_file, '{}_backup_{}'.format(destination_file, datetime.utcnow().isoformat()))
        file_ = open(destination_file, 'ab+')
        company_exporter = JsonLinesItemExporter(file_)
        company_exporter.start_exporting()
        self.items_exporter = company_exporter

    def close_spider(self, spider):
        self.items_exporter.finish_exporting()

    def _exporter_for_item(self, item):
        return self.items_exporter

    def process_item(self, item, spider):
        # if item["UID"] in self.processed_uids:
        #     raise DropItem("Duplicate item found: %s" % item)
        # self.processed_uids.add(item["UID"])
        exporter = self._exporter_for_item(item)
        exporter.export_item(item)
        return item
