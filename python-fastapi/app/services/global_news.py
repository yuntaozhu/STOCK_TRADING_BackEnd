import os
import re
import json
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import requests

# Default Gemini configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCFkoo-icWWEWz8qVlnyD-ktj-UKHbywgc")
GEMINI_MODEL = "gemini-3.5-flash"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BEIJING = timezone(timedelta(hours=8))

# Resolve paths to investment-news sources.json and data_cache.json
def get_sources_path():
    for p in [
        "/investment-news/sources.json",
        os.path.join(os.getcwd(), "..", "investment-news", "sources.json"),
        os.path.join(os.getcwd(), "investment-news", "sources.json"),
        "investment-news/sources.json"
    ]:
        if os.path.exists(p):
            return p
    return None

def get_cache_path():
    for p in [
        "/investment-news/data_cache.json",
        os.path.join(os.getcwd(), "..", "investment-news", "data_cache.json"),
        os.path.join(os.getcwd(), "investment-news", "data_cache.json"),
        "investment-news/data_cache.json"
    ]:
        # Return path even if not exists, so we can write to it
        return p
    return "/investment-news/data_cache.json"

def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

def local_tag(tag):
    return tag.split("}")[-1]

def parse_dt(s):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
    except Exception:
        try:
            dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception:
            return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

class GlobalNewsService:
    @staticmethod
    def call_gemini(system_prompt: str, user_prompt: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "aistudio-build"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=25)
            response.raise_for_status()
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return ""
        except Exception as e:
            print(f"[GlobalNewsService] Gemini API call failed: {e}")
            return ""

    @staticmethod
    def fetch_feed(src, per_source=6, cutoff=None, redline=[]):
        try:
            req = urllib.request.Request(
                src["url"], 
                headers={
                    "User-Agent": UA,
                    "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
            root = ET.fromstring(raw)
            out = []
            for n in [e for e in root.iter() if local_tag(e.tag) in ("item", "entry")]:
                if len(out) >= per_source:
                    break
                d = {"title": "", "url": "", "time": "", "ts": 0, "summary": "", "source": src["name"]}
                rawtime = ""
                for c in n:
                    t = local_tag(c.tag)
                    if t == "title" and not d["title"]:
                        d["title"] = (c.text or "").strip()
                    elif t == "link" and not d["url"]:
                        d["url"] = c.get("href") or (c.text or "").strip()
                    elif t in ("pubDate", "published", "updated", "date") and not rawtime:
                        rawtime = (c.text or "").strip()
                    elif t in ("description", "summary", "content") and not d["summary"]:
                        d["summary"] = strip_html(c.text or "")[:160]
                if not d["title"]:
                    continue
                blob = (d["title"] + " " + d["summary"]).lower()
                if any(k in blob for k in redline):
                    continue
                dt = parse_dt(rawtime)
                if dt is not None:
                    if cutoff and dt < cutoff:
                        continue
                    d["time"] = dt.astimezone(BEIJING).strftime("%m-%d %H:%M")
                    d["ts"] = int(dt.timestamp())
                else:
                    d["time"] = "—"
                out.append(d)
            return out
        except Exception as e:
            print(f"[GlobalNewsService] Error fetching source {src['name']}: {e}")
            return []

    @classmethod
    def get_news_data(cls, force_fetch=False) -> dict:
        cache_file = get_cache_path()
        if not force_fetch and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[GlobalNewsService] Failed to load cache: {e}")

        # Cache file not found or force refresh requested, do a fresh quick fetch
        return cls.refresh_news_feed_data()

    @classmethod
    def refresh_news_feed_data(cls, recent_days=7) -> dict:
        sources_file = get_sources_path()
        if not sources_file:
            # Fallback if config is totally missing
            return {"generated_at": "", "industries": [], "stats": {"industries": 0, "total_sources": 0}}

        try:
            with open(sources_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[GlobalNewsService] Failed to read sources.json: {e}")
            return {"generated_at": "", "industries": [], "stats": {"industries": 0, "total_sources": 0}}

        days = cfg.get("fetch", {}).get("recent_days", recent_days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        redline = [k.lower() for k in cfg.get("redline_keywords", [])]
        inds = cfg["industries"]
        byhint = {}
        for s in cfg["sources"]:
            byhint.setdefault(s["hint"], []).append(s)

        industries = []
        tasks = []
        for i, ind in enumerate(inds):
            pool = byhint.get(ind["key"], [])
            industries.append({
                "key": ind["key"],
                "name": ind["name"],
                "accent": ind["accent"],
                "total": len(pool),
                "items": [],
                "points": [],
                "has_ai": False
            })
            for s in pool:
                tasks.append((i, s))

        # Parallel fetch using ThreadPool
        per_source = cfg.get("fetch", {}).get("per_source", 6)
        with ThreadPoolExecutor(max_workers=30) as ex:
            results = list(ex.map(lambda t: (t[0], cls.fetch_feed(t[1], per_source, cutoff, redline)), tasks))

        for idx, items in results:
            industries[idx]["items"].extend(items)

        # Sort each industry sector feeds by timestamp descending
        for ind in industries:
            ind["items"].sort(key=lambda x: x.get("ts", 0), reverse=True)

        data = {
            "generated_at": datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M"),
            "recent_days": days,
            "industries": industries,
            "stats": {
                "industries": len(inds),
                "total_sources": len(cfg["sources"])
            }
        }

        # Write to cache file
        cache_file = get_cache_path()
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[GlobalNewsService] Failed to write cache: {e}")

        return data

    @classmethod
    def digest_sector(cls, sector_key: str) -> dict:
        """
        Dynamically digests a specific sector key using Gemini, translating non-Chinese titles
        and generating key points, then updates the saved cache and returns the updated sector.
        """
        # Load cache data
        cache_data = cls.get_news_data()
        industries = cache_data.get("industries", [])
        
        # Find target sector
        target_ind = None
        for ind in industries:
            if ind["key"] == sector_key:
                target_ind = ind
                break

        if not target_ind or not target_ind.get("items"):
            return {"success": False, "error": "Sector not found or empty"}

        items = target_ind["items"][:16] # TOP 16 items as in digest.py
        
        # Prepare Gemini prompt
        system_prompt = (
            "你是中文行业新闻分析助手。给你某行业最近的新闻列表(每条带序号),请做两件事:\n"
            "1) 提炼 3-5 条「今日要点」:聚合最重要的行业动向,每条不超过 40 字,可合并同类、突出数字/公司/趋势,客观陈述。"
            "每条要点用 refs 标注它主要来自哪几条新闻的序号(用于跳转原文,至少 1 个)。\n"
            "2) 给每条新闻一个简洁准确的中文标题翻译;若原文已是中文则原样返回。\n"
            "只输出 JSON,不要任何解释或代码块标记。格式:\n"
            '{"points":[{"t":"要点1","refs":[0,3]},{"t":"要点2","refs":[5]}],"items":[{"i":0,"zh":"中文标题"}]}'
        )
        
        user_lines = [f"行业:{target_ind['name']}", "新闻:"]
        for idx, item in enumerate(items):
            user_lines.append(f"{idx}. {item['title']} ({item.get('source', '')})")
        user_prompt = "\n".join(user_lines)

        # Call Gemini
        gemini_response = cls.call_gemini(system_prompt, user_prompt)
        if not gemini_response:
            return {"success": False, "error": "AI digestion failed"}

        # Extract and parse JSON response
        try:
            # Strip code block decorators if model mistakenly outputs them
            cleaned_resp = gemini_response.strip()
            if cleaned_resp.startswith("```"):
                # strip lead and trail ```
                cleaned_resp = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned_resp)
                cleaned_resp = re.sub(r"\s*```$", "", cleaned_resp)
            
            d = json.loads(cleaned_resp)
        except Exception as e:
            print(f"[GlobalNewsService] JSON decoding failed: {e}. Raw response: {gemini_response}")
            return {"success": False, "error": f"Failed to parse AI output: {e}"}

        # Build clean points lists with reference urls
        pts = []
        for p in d.get("points", [])[:5]:
            if isinstance(p, dict):
                t = (p.get("t") or "").strip()
                url = ""
                for r in p.get("refs", []):
                    if isinstance(r, int) and 0 <= r < len(items) and items[r].get("url"):
                        url = items[r]["url"]
                        break
                if t:
                    pts.append({"t": t, "url": url})
            elif isinstance(p, str) and p.strip():
                pts.append({"t": p.strip(), "url": ""})

        target_ind["points"] = pts
        
        # Apply translation mapping
        zh_map = {x.get("i"): x.get("zh", "") for x in d.get("items", []) if isinstance(x, dict)}
        for idx, item in enumerate(items):
            item["zh"] = zh_map.get(idx, "")

        target_ind["items"] = items
        target_ind["has_ai"] = True

        # Save back to cache file
        cache_file = get_cache_path()
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[GlobalNewsService] Failed to save updated cache: {e}")

        return {"success": True, "sector": target_ind}
