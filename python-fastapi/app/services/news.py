import re
import json
import uuid
import requests
from app.core.limiter import em_get

class NewsService:
    @staticmethod
    def get_eastmoney_stock_news(code: str, page_size: int = 20) -> list[dict]:
        """
        Retrieves real-time individual news articles for a stock.
        """
        # Strip code of prefix to match Eastmoney's search parameters
        from app.services.base import clean_code
        cleaned = clean_code(code)
        
        cb = "jQuery_news"
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        
        inner_param = {
            "uid": "",
            "keyword": cleaned,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default", 
                    "sort": "default",
                    "pageIndex": 1, 
                    "pageSize": page_size, 
                    "preTag": "", 
                    "postTag": ""
                }
            },
        }
        params = {
            "cb": cb, 
            "param": json.dumps(inner_param, separators=(',', ':'))
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://so.eastmoney.com/"
        }
        try:
            r = em_get(url, params=params, headers=headers, timeout=15)
            text = r.text
            # Extract JSON from JSONP callback
            start_idx = text.index("(") + 1
            end_idx = text.rindex(")")
            json_str = text[start_idx:end_idx]
            d = json.loads(json_str)
            
            rows = []
            articles = d.get("result", {}).get("cmsArticleWebOld", []) or []
            for a in articles:
                rows.append({
                    "title": re.sub(r'<[^>]+>', '', a.get("title", "")),
                    "content": re.sub(r'<[^>]+>', '', a.get("content", ""))[:200],
                    "time": a.get("date", ""),
                    "source": a.get("mediaName", ""),
                    "url": a.get("url", ""),
                })
            return rows
        except Exception as e:
            return []

    @staticmethod
    def get_eastmoney_global_news(page_size: int = 50) -> list[dict]:
        """
        Retrieves real-time 7x24 global financial news feeds.
        """
        url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
        params = {
            "client": "web", 
            "biz": "web_724",
            "fastColumn": "102", 
            "sortEnd": "",
            "pageSize": str(page_size),
            "req_trace": str(uuid.uuid4()),
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://kuaixun.eastmoney.com/"
        }
        try:
            r = em_get(url, params=params, headers=headers, timeout=10)
            d = r.json()
            items = d.get("data", {}).get("fastNewsList", []) or []
            rows = []
            for item in items:
                rows.append({
                    "title": item.get("title", ""),
                    "summary": item.get("summary", "")[:200],
                    "time": item.get("showTime", ""),
                })
            return rows
        except Exception as e:
            return []
