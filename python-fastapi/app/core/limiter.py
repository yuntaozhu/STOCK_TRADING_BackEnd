import time
import random
import logging
import requests
from app.config import settings

logger = logging.getLogger("a_stock.limiter")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

# Global session reuse for Eastmoney to enable Keep-Alive and prevent connection errors
EM_SESSION = requests.Session()
EM_SESSION.headers.update({"User-Agent": UA})

class EastmoneyLimiter:
    """
    Unified rate limiter and session manager for all Eastmoney API requests.
    Prevents triggering anti-bot bans by enforcing minimum call intervals
    with random jitter, utilizing HTTP connection pooling.
    """
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_call_time = 0.0

    def get(self, url: str, params: dict = None, headers: dict = None, timeout: int = 15, **kwargs):
        # Calculate time since last call and sleep if needed to respect throttling threshold
        now = time.time()
        elapsed = now - self.last_call_time
        wait = self.min_interval - elapsed
        
        if wait > 0:
            jitter = random.uniform(0.1, 0.5)
            time.sleep(wait + jitter)
            
        merged_headers = {"User-Agent": UA}
        if headers:
            merged_headers.update(headers)
            
        try:
            logger.debug(f"Throttled GET Request: {url}")
            response = EM_SESSION.get(url, params=params, headers=merged_headers, timeout=timeout, **kwargs)
            return response
        finally:
            self.last_call_time = time.time()

# Singleton instance of the limiter
limiter = EastmoneyLimiter(min_interval=settings.EM_MIN_INTERVAL)

def em_get(url: str, params: dict = None, headers: dict = None, timeout: int = 15, **kwargs):
    """
    Global helper function to perform safe throttled GET requests to Eastmoney.
    """
    return limiter.get(url, params=params, headers=headers, timeout=timeout, **kwargs)

def eastmoney_datacenter(report_name: str, columns: str = "ALL",
                          filter_str: str = "", page_size: int = 50,
                          sort_columns: str = "", sort_types: str = "-1") -> list[dict]:
    """
    Unified datacenter query helper for Eastmoney (shared by dragon tiger list, block trades,
    margin trading, lockups, holders, and dividends).
    """
    params = {
        "reportName": report_name, 
        "columns": columns,
        "filter": filter_str, 
        "pageNumber": "1", 
        "pageSize": str(page_size),
        "sortColumns": sort_columns, 
        "sortTypes": sort_types,
        "source": "WEB", 
        "client": "WEB",
    }
    try:
        r = em_get(DATACENTER_URL, params=params, timeout=15)
        d = r.json()
        if d.get("result") and d["result"].get("data"):
            return d["result"]["data"]
    except Exception as e:
        logger.error(f"Error querying Eastmoney Datacenter [{report_name}]: {e}")
    return []
