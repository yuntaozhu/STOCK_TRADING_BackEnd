import os
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
from app.core.limiter import em_get, eastmoney_datacenter
from app.services.base import clean_code

HSGT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Host": "data.hexin.cn",
    "Referer": "https://data.hexin.cn/",
}

class SignalsService:
    @staticmethod
    def get_ths_hot_reason(date_str: str = None) -> list[dict]:
        """
        Retrieves real-time daily leading stocks and their thematic tags (reason).
        """
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")

        url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date_str}/orderby/date/orderway/desc/charset/GBK/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }
        try:
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            if data.get("errocode", 0) != 0:
                raise RuntimeError(f"THS hot reason error: {data.get('errormsg')}")
            rows = data.get("data") or []
            return rows
        except Exception as e:
            raise RuntimeError(f"Error calling THS Hot Reason API: {e}")

    @staticmethod
    def get_hsgt_realtime() -> list[dict]:
        """
        Retrieves current minute-by-minute northbound cumulative capital flow.
        """
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
        try:
            r = requests.get(url, headers=HSGT_HEADERS, timeout=10)
            d = r.json()
            times = d.get("time", [])
            hgt = d.get("hgt", [])
            sgt = d.get("sgt", [])
            
            n = len(times)
            result = []
            for i in range(n):
                result.append({
                    "time": times[i],
                    "hgt_yi": hgt[i] if i < len(hgt) else None,
                    "sgt_yi": sgt[i] if i < len(sgt) else None,
                })
            return result
        except Exception as e:
            raise RuntimeError(f"Error calling HSGT Realtime API: {e}")

    @staticmethod
    def get_eastmoney_concept_blocks(code: str) -> dict:
        """
        Retrieves concept/industry sectors associated with a specific stock.
        """
        cleaned = clean_code(code)
        market_code = 1 if cleaned.startswith("6") else 0
        params = {
            "fltt": "2", "invt": "2",
            "secid": f"{market_code}.{cleaned}",
            "spt": "3", "pi": "0", "pz": "200", "po": "1",
            "fields": "f12,f14,f3,f128",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/"
        }
        try:
            r = em_get("https://push2.eastmoney.com/api/qt/slist/get", params=params, headers=headers, timeout=15)
            d = r.json()
            diff = (d.get("data") or {}).get("diff") or {}
            items = diff.values() if isinstance(diff, dict) else diff
            boards = []
            for it in items:
                boards.append({
                    "name": it.get("f14", ""),
                    "code": it.get("f12", ""),
                    "change_pct": it.get("f3", 0.0),
                    "lead_stock_code": it.get("f128", ""),
                })
            return {
                "total": len(boards),
                "boards": boards,
                "concept_tags": [b["name"] for b in boards]
            }
        except Exception as e:
            # Safe fallback
            return {"total": 0, "boards": [], "concept_tags": []}

    @staticmethod
    def get_eastmoney_fund_flow_minute(code: str) -> list[dict]:
        """
        Retrieves real-time intraday minute-level fund flow trends for a stock.
        """
        cleaned = clean_code(code)
        secid = f"1.{cleaned}" if cleaned.startswith("6") else f"0.{cleaned}"
        url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        params = {
            "secid": secid, "klt": 1,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/",
        }
        try:
            r = em_get(url, params=params, headers=headers, timeout=10)
            d = r.json()
            klines = d.get("data", {}).get("klines", []) or []
            rows = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 6:
                    rows.append({
                        "time": parts[0],
                        "main_net": float(parts[1]) if parts[1] != "-" else 0.0,
                        "small_net": float(parts[2]) if parts[2] != "-" else 0.0,
                        "mid_net": float(parts[3]) if parts[3] != "-" else 0.0,
                        "large_net": float(parts[4]) if parts[4] != "-" else 0.0,
                        "super_net": float(parts[5]) if parts[5] != "-" else 0.0,
                    })
            return rows
        except Exception as e:
            return []

    @staticmethod
    def get_dragon_tiger_board(code: str, trade_date: str, look_back: int = 30) -> dict:
        """
        Aggregates Dragon-Tiger board appearances, buy/sell seats, and institutional volume.
        """
        cleaned = clean_code(code)
        try:
            start = datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)
            start_str = start.strftime("%Y-%m-%d")
        except ValueError:
            start_str = (datetime.now() - timedelta(days=look_back)).strftime("%Y-%m-%d")

        # 1. Historical appearance list
        records = []
        data = eastmoney_datacenter(
            "RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_str=f"(TRADE_DATE>='{start_str}')(TRADE_DATE<='{trade_date}')(SECURITY_CODE=\"{cleaned}\")",
            page_size=50,
            sort_columns="TRADE_DATE", sort_types="-1",
        )
        for row in data:
            records.append({
                "date": str(row.get("TRADE_DATE", ""))[:10],
                "reason": row.get("EXPLANATION", ""),
                "net_buy": round((row.get("BILLBOARD_NET_AMT") or 0) / 10000, 1),
                "turnover": round(float(row.get("TURNOVERRATE") or 0), 2),
            })

        seats = {"buy": [], "sell": []}
        institution = {"buy_amt": 0, "sell_amt": 0, "net_amt": 0}
        
        # 2. Extract buy/sell details if there is a record
        if records:
            latest_date = records[0]["date"]
            
            # Fetch Buy detail records
            buy_data = eastmoney_datacenter(
                "RPT_BILLBOARD_DAILYDETAILSBUY",
                filter_str=f"(TRADE_DATE='{latest_date}')(SECURITY_CODE=\"{cleaned}\")",
                page_size=10,
                sort_columns="BUY", sort_types="-1",
            )
            for row in buy_data[:5]:
                seats["buy"].append({
                    "name": row.get("OPERATEDEPT_NAME", ""),
                    "buy_amt": round((row.get("BUY") or 0) / 10000, 1),
                    "sell_amt": round((row.get("SELL") or 0) / 10000, 1),
                    "net": round((row.get("NET") or 0) / 10000, 1),
                })
                
            # Fetch Sell detail records
            sell_data = eastmoney_datacenter(
                "RPT_BILLBOARD_DAILYDETAILSSELL",
                filter_str=f"(TRADE_DATE='{latest_date}')(SECURITY_CODE=\"{cleaned}\")",
                page_size=10,
                sort_columns="SELL", sort_types="-1",
            )
            for row in sell_data[:5]:
                seats["sell"].append({
                    "name": row.get("OPERATEDEPT_NAME", ""),
                    "buy_amt": round((row.get("BUY") or 0) / 10000, 1),
                    "sell_amt": round((row.get("SELL") or 0) / 10000, 1),
                    "net": round((row.get("NET") or 0) / 10000, 1),
                })

            # Calculate institutional buy and sell aggregates (OPERATEDEPT_CODE="0")
            for detail_data, side in [(buy_data, "buy"), (sell_data, "sell")]:
                for row in detail_data:
                    if str(row.get("OPERATEDEPT_CODE", "")) == "0":
                        amt = (row.get("BUY") or 0) if side == "buy" else (row.get("SELL") or 0)
                        if side == "buy":
                            institution["buy_amt"] += amt
                        else:
                            institution["sell_amt"] += amt
                            
            institution["buy_amt"] = round(institution["buy_amt"] / 10000, 1)
            institution["sell_amt"] = round(institution["sell_amt"] / 10000, 1)
            institution["net_amt"] = round(institution["buy_amt"] - institution["sell_amt"], 1)

        return {"records": records, "seats": seats, "institution": institution}

    @staticmethod
    def get_lockup_expiry(code: str, trade_date: str, forward_days: int = 90) -> dict:
        """
        Retrieves historical and upcoming stock lockup expiries.
        """
        cleaned = clean_code(code)
        # Historical expiries
        history_data = eastmoney_datacenter(
            "RPT_LIFT_STAGE",
            filter_str=f"(SECURITY_CODE=\"{cleaned}\")",
            page_size=15,
            sort_columns="FREE_DATE", sort_types="-1",
        )
        history = []
        for row in history_data:
            history.append({
                "date": str(row.get("FREE_DATE", ""))[:10],
                "type": row.get("LIMITED_STOCK_TYPE", ""),
                "shares": row.get("FREE_SHARES_NUM", 0),
                "ratio": row.get("FREE_RATIO", 0),
            })

        # Future upcoming expiries
        try:
            end_date = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=forward_days)
            end_str = end_date.strftime("%Y-%m-%d")
        except ValueError:
            end_str = (datetime.now() + timedelta(days=forward_days)).strftime("%Y-%m-%d")

        upcoming_data = eastmoney_datacenter(
            "RPT_LIFT_STAGE",
            filter_str=f"(SECURITY_CODE=\"{cleaned}\")(FREE_DATE>='{trade_date}')(FREE_DATE<='{end_str}')",
            page_size=20,
            sort_columns="FREE_DATE", sort_types="1",
        )
        upcoming = []
        for row in upcoming_data:
            upcoming.append({
                "date": str(row.get("FREE_DATE", ""))[:10],
                "type": row.get("LIMITED_STOCK_TYPE", ""),
                "shares": row.get("FREE_SHARES_NUM", 0),
                "ratio": row.get("FREE_RATIO", 0),
            })

        return {"history": history, "upcoming": upcoming}

    @staticmethod
    def get_industry_comparison(top_n: int = 20) -> dict:
        """
        Retrieves the industry-wide sector leaderboard to monitor sector rotation and capital inflow.
        """
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1", "pz": "100", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:90+t:2",
            "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = em_get(url, params=params, headers=headers, timeout=15)
            d = r.json()
            items = d.get("data", {}).get("diff", []) or []
            rows = []
            for i, item in enumerate(items):
                rows.append({
                    "rank": i + 1,
                    "name": item.get("f14", ""),
                    "change_pct": item.get("f3", 0.0),
                    "code": item.get("f12", ""),
                    "up_count": item.get("f104", 0),
                    "down_count": item.get("f105", 0),
                    "leader": item.get("f140", ""),
                    "leader_change": item.get("f136", 0.0),
                })
            return {
                "top": rows[:top_n],
                "bottom": rows[-top_n:] if len(rows) >= top_n else rows,
                "total": len(rows),
            }
        except Exception as e:
            return {"top": [], "bottom": [], "total": 0}

    @staticmethod
    def get_daily_dragon_tiger(trade_date: str = None, min_net_buy: float = None) -> dict:
        """
        Summarizes the entire market's daily dragon-tiger board.
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        data = eastmoney_datacenter(
            "RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_str=f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
            page_size=500,
            sort_columns="BILLBOARD_NET_AMT", sort_types="-1",
        )
        if not data:
            return {"date": trade_date, "total_records": 0, "stocks": []}

        actual_date = str(data[0].get("TRADE_DATE", ""))[:10]
        stocks = []
        for row in data:
            net_buy = (row.get("BILLBOARD_NET_AMT") or 0) / 10000
            if min_net_buy is not None and net_buy < min_net_buy:
                continue
            stocks.append({
                "code": row.get("SECURITY_CODE", ""),
                "name": row.get("SECURITY_NAME_ABBR", ""),
                "reason": row.get("EXPLANATION", ""),
                "close": row.get("CLOSE_PRICE") or 0.0,
                "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
                "net_buy_wan": round(net_buy, 1),
                "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
                "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
                "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
            })
        return {"date": actual_date, "total_records": len(stocks), "stocks": stocks}
