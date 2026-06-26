import urllib.request
import requests
from app.core.mootdx_client import tdx_client
from app.services.base import clean_code, get_prefix

class MarketService:
    @staticmethod
    def get_mootdx_kline(code: str, category: int = 4, offset: int = 100):
        """
        Retrieves K-line historical data from mootdx TCP.
        category: 4=daily, 5=weekly, 6=monthly, 7=1min, 8=5min, 9=15min, 10=30min, 11=60min
        """
        cleaned = clean_code(code)
        try:
            client = tdx_client()
            df = client.bars(symbol=cleaned, category=category, offset=offset)
            if df is not None and not df.empty:
                # Reset index to include datetime or date column in json output
                df = df.reset_index()
                if 'datetime' in df.columns:
                    df['datetime'] = df['datetime'].astype(str)
                return df.to_dict(orient="records")
        except Exception as e:
            raise RuntimeError(f"mootdx K-line error: {e}")
        return []

    @staticmethod
    def get_mootdx_quotes(symbols: list[str]):
        """
        Retrieves raw live 5-level order book and quotes from mootdx TCP.
        """
        cleaned_symbols = [clean_code(s) for s in symbols]
        try:
            client = tdx_client()
            df = client.quotes(symbol=cleaned_symbols)
            if df is not None and not df.empty:
                return df.reset_index().to_dict(orient="records")
        except Exception as e:
            raise RuntimeError(f"mootdx quotes error: {e}")
        return []

    @staticmethod
    def get_mootdx_transactions(code: str, date: str = None):
        """
        Retrieves tick-by-tick real-time transaction records for the given date.
        """
        cleaned = clean_code(code)
        try:
            client = tdx_client()
            df = client.transaction(symbol=cleaned, date=date)
            if df is not None and not df.empty:
                return df.reset_index().to_dict(orient="records")
        except Exception as e:
            raise RuntimeError(f"mootdx transaction error: {e}")
        return []

    @staticmethod
    def get_tencent_quotes(codes: list[str]) -> dict:
        """
        Retrieves live stock stats including valuation (PE/PB), limits and turnover via Tencent.
        """
        prefixed = []
        for c in codes:
            cleaned = clean_code(c)
            prefix = get_prefix(cleaned)
            prefixed.append(f"{prefix}{cleaned}")
            
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read().decode("gbk")
        except Exception as e:
            raise RuntimeError(f"Tencent API request failed: {e}")

        result = {}
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            result[code] = {
                "name":         vals[1],
                "price":        float(vals[3]) if vals[3] else 0,
                "last_close":   float(vals[4]) if vals[4] else 0,
                "open":         float(vals[5]) if vals[5] else 0,
                "change_amt":   float(vals[31]) if vals[31] else 0,
                "change_pct":   float(vals[32]) if vals[32] else 0,
                "high":         float(vals[33]) if vals[33] else 0,
                "low":          float(vals[34]) if vals[34] else 0,
                "amount_wan":   float(vals[37]) if vals[37] else 0,
                "turnover_pct": float(vals[38]) if vals[38] else 0,
                "pe_ttm":       float(vals[39]) if vals[39] else 0,
                "amplitude_pct":float(vals[43]) if vals[43] else 0,
                "mcap_yi":      float(vals[44]) if vals[44] else 0,
                "float_mcap_yi":float(vals[45]) if vals[45] else 0,
                "pb":           float(vals[46]) if vals[46] else 0,
                "limit_up":     float(vals[47]) if vals[47] else 0,
                "limit_down":   float(vals[48]) if vals[48] else 0,
                "vol_ratio":    float(vals[49]) if vals[49] else 0,
                "pe_static":    float(vals[52]) if vals[52] else 0,
            }
        return result

    @staticmethod
    def get_baidu_kline(code: str, start_time: str = "") -> dict:
        """
        Retrieves K-line historical data directly calculated with MA5/MA10/MA20 metrics from Baidu.
        """
        cleaned = clean_code(code)
        url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
        params = {
            "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
            "isFutures": "false", "isStock": "true", "newFormat": "1",
            "group": "quotation_kline_ab", "finClientType": "pc",
            "code": cleaned, "start_time": start_time, "ktype": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.finance-web.v1+json",
            "Origin": "https://gushitong.baidu.com",
            "Referer": "https://gushitong.baidu.com/",
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            d = r.json()
            if d.get("ResultCode") == 0 or d.get("ResultCode") == "0":
                result = d.get("Result", {})
                md = result.get("newMarketData", {})
                keys = md.get("keys", [])
                rows = md.get("marketData", "").split(";")
                return {"keys": keys, "rows": rows}
        except Exception as e:
            raise RuntimeError(f"Baidu K-line request failed: {e}")
        return {"keys": [], "rows": []}
