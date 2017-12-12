from scrapy_redis.spiders import RedisCrawlSpider
from scrapy.spiders import Rule
from scrapy import Request, Spider
import json
import requests
from lxml import etree
import re
from mt_spider.items import JsonItem


class MTSpider(Spider):
    name = 'mt'
    city = '上海'
    ci = 0

    def start_requests(self):
        """获取城市链接，以便从请求后返回的cookie中获取城市代码"""
        response = requests.get('https://i.meituan.com/index/changecity', cookies={})
        html = etree.HTML(response.text)
        for selector in html.xpath('//*[@id="cityBox"]/div[@class="box nopadding"]/div[@class="abc"]/ul/li/a'):
            if selector.xpath('text()').pop() == self.city:
                url = selector.xpath('@href').pop()
                url = 'https:{}'.format(url)
                yield Request(url, callback=self.parse_start_url)

    @staticmethod
    def get_ci(response):
        """获取城市代码ci"""
        for k, v in response.headers.items():
            if k == b'Set-Cookie':
                for i in v:
                    s = i.decode()
                    ci = re.findall('ci=(\d+);', s)
                    if ci:
                        ci = ci.pop()
                        return ci
                break
        return None

    def parse_start_url(self, response):
        self.ci = self.get_ci(response)
        cookies = {
            'uuid': 'e2cf127f-e136-4269-a295-adcf43be5ae5',
            'IJSESSIONID': 'juv2xkp7fya11597k3cwxvxdk',
            'iuuid': 'B64E3DF0E1229F91B9AC39AEAF6F06E2A1549329005005C283CDA0D3D9763E61',
            'ci': self.ci,
            'cityname': '%E9%9A%8F%E5%B7%9E',
            'client-id': '85e42834-a08c-436f-99c3-3861a91f9851'
        }
        yield Request('https://meishi.meituan.com/i/', cookies=cookies, callback=self.parse_city_url)

    def get_area_id_list(self, script):
        """获取当前城市的areaId列表"""
        area_id_list = {}
        if script:
            name, arr = script.strip(';').split('=', 1)
            arr = json.loads(arr)
            for j in arr.items():
                if j[0] == 'navBarData':
                    area_list = j[1].get('areaList')
                    area_obj = j[1].get('areaObj')
                    for area in area_list:
                        area_id = area.get('id', 0)
                        if area_id > 0:
                            count = area.get('count', 0)
                            # Ajax下拉超过900条不返回数据，数据大于900条的查询分类地区
                            if count >= 900:
                                area_obj_list = area_obj.get(str(area_id))
                                for area_ in area_obj_list:
                                    area_name = area_.get('name', '全部')
                                    if area_name != '全部':
                                        count = area_.get('count', 0)
                                        area_id = area_.get('id', 0)
                                        area_id_list[area_id] = count
                            else:
                                area_id_list[area_id] = count
        return area_id_list

    def parse_city_url(self, response):
        """这里我们以areaId为关键字向服务器post请求"""
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
            'x-requested-with': 'XMLHttpRequest',
        }

        cookies = {
            'uuid': 'e2cf127f-e136-4269-a295-adcf43be5ae5',
            'IJSESSIONID': 'juv2xkp7fya11597k3cwxvxdk',
            'iuuid': 'B64E3DF0E1229F91B9AC39AEAF6F06E2A1549329005005C283CDA0D3D9763E61',
            'ci': self.ci,
            'cityname': '%E9%9A%8F%E5%B7%9E',
            'client-id': '85e42834-a08c-436f-99c3-3861a91f9851'
        }
        script = response.xpath('//script[starts-with(text(),"window._appState")]/text()').extract().pop()
        area_id_list = self.get_area_id_list(script)
        for area_id, count in area_id_list.items():
            try:
                count = int(count)
            except:
                count = 0
            """构造post数据"""
            data = {"offset": 0, "limit": 50, "cateId": 1, "lineId": 0, "stationId": 0,
                    "areaId": area_id, "sort": "default",
                    "deal_attr_23": "", "deal_attr_24": "", "deal_attr_25": "", "poi_attr_20043": "",
                    "poi_attr_20033": ""}
            while data['offset'] < count:
                yield Request(url='http://meishi.meituan.com/i/api/channel/deal/list', method='post', cookies=cookies,
                              headers=headers, body=json.dumps(data), callback=self.parse_item)
                data['offset'] += data['limit']

    def parse_item(self, response):
        datas = json.loads(response.body_as_unicode())
        data = datas.get('data')
        poiList = data.get('poiList') if data else None
        poi_infos = poiList.get('poiInfos') if poiList else None
        for poi_info in poi_infos:
            yield JsonItem(poiInfo=poi_info)
