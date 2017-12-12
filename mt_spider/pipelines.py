# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json

class MtSpiderPipeline(object):
    def __init__(self):
        self.f = open('item.json','w+')

    def process_item(self, item, spider):
        self.f.write(json.dumps(dict(item), ensure_ascii=False) + '\n')
        return item

    def close_spider(self):
        print('关闭')
        self.f.close()
