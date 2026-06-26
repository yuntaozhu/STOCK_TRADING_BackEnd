import re
import os
import json
import secrets
import requests
import pandas as pd
from io import StringIO
from pathlib import Path
from app.config import settings
from app.core.limiter import em_get
from app.services.base import clean_code

REPORT_API = "https://reportapi.eastmoney.com/report/list"
PDF_TPL = "https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"

class ReportsService:
    @staticmethod
    def get_eastmoney_stock_reports(code: str, max_pages: int = 5) -> list[dict]:
        """
        Retrieves analyst research reports for a specific stock ticker.
        """
        cleaned = clean_code(code)
        all_records = []
        for page in range(1, max_pages + 1):
            params = {
                "industryCode": "*", "pageSize": "100", "industry": "*",
                "rating": "*", "ratingChange": "*",
                "beginTime": "2000-01-01", "endTime": "2030-01-01",
                "pageNo": str(page), "fields": "", "qType": "0",
                "orgCode": "", "code": cleaned, "rcode": "",
                "p": str(page), "pageNum": str(page), "pageNumber": str(page),
            }
            try:
                r = em_get(REPORT_API, params=params, headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)
                d = r.json()
                rows = d.get("data") or []
                if not rows:
                    break
                all_records.extend(rows)
                if page >= (d.get("TotalPage", 1) or 1):
                    break
            except Exception as e:
                # Log error and return whatever we got so far
                break
        return all_records

    @staticmethod
    def get_eastmoney_industry_reports(industry_code: str = "*", max_pages: int = 5, begin: str = "2024-01-01") -> list[dict]:
        """
        Retrieves industry-wide macro and micro thematic research reports.
        """
        all_records = []
        for page in range(1, max_pages + 1):
            params = {
                "industryCode": industry_code, "pageSize": "100", "industry": "*",
                "rating": "*", "ratingChange": "*",
                "beginTime": begin, "endTime": "2030-01-01",
                "pageNo": str(page), "fields": "", "qType": "1",
            }
            try:
                r = em_get(REPORT_API, params=params, headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)
                d = r.json()
                rows = d.get("data") or []
                if not rows:
                    break
                all_records.extend(rows)
                if page >= (d.get("TotalPage", 1) or 1):
                    break
            except Exception as e:
                break
        return all_records

    @staticmethod
    def download_report_pdf(info_code: str, title: str, org_sname: str, publish_date: str, target_dir: str = "./reports") -> str:
        """
        Downloads a research report as PDF. Respects Referer header requirements to avoid 403.
        """
        if not info_code:
            raise ValueError("info_code is required")
        
        date = publish_date[:10] if publish_date else "unknown"
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:80]
        fname = f"{date}_{org_sname}_{safe_title}.pdf"
        target_path = Path(target_dir) / fname
        
        if target_path.exists():
            return str(target_path.absolute())
            
        url = PDF_TPL.format(info_code=info_code)
        try:
            r = em_get(url, headers={"Referer": "https://data.eastmoney.com/"}, timeout=60)
            if r.status_code == 200 and len(r.content) >= 1024:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(r.content)
                return str(target_path.absolute())
            else:
                raise RuntimeError(f"Download failed with status {r.status_code} or small size")
        except Exception as e:
            raise RuntimeError(f"Error downloading PDF {info_code}: {e}")

    @staticmethod
    def get_ths_forecast(code: str) -> list[dict]:
        """
        Parses Tonghuashun consensus forecast table.
        """
        cleaned = clean_code(code)
        url = f"https://basic.10jqka.com.cn/new/{cleaned}/worth.html"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://basic.10jqka.com.cn/",
        }
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.encoding = "gbk"
            dfs = pd.read_html(StringIO(r.text))
            target_df = None
            for df in dfs:
                cols = [str(c) for c in df.columns]
                if any("每股收益" in c or "均值" in c for c in cols):
                    target_df = df
                    break
            
            if target_df is None and dfs:
                target_df = dfs[0]
                
            if target_df is not None and not target_df.empty:
                # Standardize columns to string
                target_df.columns = [str(c) for c in target_df.columns]
                return target_df.to_dict(orient="records")
        except Exception as e:
            # Let it fail gracefully returning empty list
            pass
        return []

    @staticmethod
    def _claw_headers(call_type: str = "normal") -> dict:
        """Required X-Claw headers for iwencai 2.0 validation"""
        return {
            "X-Claw-Call-Type": call_type,
            "X-Claw-Skill-Id": "report-search",
            "X-Claw-Skill-Version": "2.0.0",
            "X-Claw-Plugin-Id": "none",
            "X-Claw-Plugin-Version": "none",
            "X-Claw-Trace-Id": secrets.token_hex(32),
        }

    @classmethod
    def search_iwencai(cls, query: str, channel: str = "report", size: int = 50) -> list[dict]:
        """
        Semantic NLP search across research reports, announcements or news using iwencai.
        """
        if not settings.IWENCAI_API_KEY:
            raise ValueError("IWENCAI_API_KEY environment variable is not configured")
            
        headers = {
            "Authorization": f"Bearer {settings.IWENCAI_API_KEY}",
            "Content-Type": "application/json",
            **cls._claw_headers(),
        }
        payload = {
            "channels": [channel],
            "app_id": "AIME_SKILL",
            "query": query,
            "size": size,
        }
        try:
            r = requests.post(
                f"{settings.IWENCAI_BASE_URL}/v1/comprehensive/search",
                json=payload, headers=headers, timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status_code", 0) != 0:
                raise RuntimeError(f"iwencai query failed: {data.get('status_msg')}")
            return data.get("data") or []
        except Exception as e:
            raise RuntimeError(f"iwencai connection error: {e}")

    @classmethod
    def query_iwencai_data(cls, query: str, page: int = 1, limit: int = 50) -> list[dict]:
        """
        Extracts structured financial rows from natural language queries via iwencai.
        """
        if not settings.IWENCAI_API_KEY:
            raise ValueError("IWENCAI_API_KEY environment variable is not configured")
            
        headers = {
            "Authorization": f"Bearer {settings.IWENCAI_API_KEY}",
            "Content-Type": "application/json",
            **cls._claw_headers(),
        }
        payload = {
            "query": query,
            "page": str(page),
            "limit": str(limit),
            "is_cache": "1",
            "expand_index": "true",
        }
        try:
            r = requests.post(
                f"{settings.IWENCAI_BASE_URL}/v1/query2data",
                json=payload, headers=headers, timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status_code", 0) != 0:
                raise RuntimeError(f"iwencai data extraction failed: {data.get('status_msg')}")
            return data.get("datas") or []
        except Exception as e:
            raise RuntimeError(f"iwencai connection error: {e}")
            
    @staticmethod
    def dedup_articles(articles: list[dict]) -> list[dict]:
        """Helper to deduplicate iwencai search blocks by maintaining highest scored record per uid"""
        best = {}
        for a in articles:
            uid = a.get("uid", "") or f"{a.get('title','')}|{a.get('publish_date','')}"
            score = float(a.get("score", 0))
            if uid not in best or score > float(best[uid].get("score", 0)):
                best[uid] = a
        return sorted(best.values(), key=lambda x: x.get("publish_date", ""), reverse=True)
