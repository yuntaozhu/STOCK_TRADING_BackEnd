import math
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import FileResponse
from typing import List, Optional

# Import services
from app.services.market import MarketService
from app.services.reports import ReportsService
from app.services.signals import SignalsService
from app.services.capital import CapitalService
from app.services.news import NewsService
from app.services.financials import FinancialsService
from app.services.announcements import AnnouncementsService

router = APIRouter(prefix="/api")

# =====================================================================
# LAYER 1: 行情层 (MARKET)
# =====================================================================

@router.get("/market/kline", tags=["Market"])
def get_kline(code: str, category: int = 4, offset: int = 100):
    """mootdx TCP 行情 K线"""
    return MarketService.get_mootdx_kline(code, category, offset)

@router.get("/market/quotes", tags=["Market"])
def get_quotes(symbols: str = Query(..., description="Comma separated tickers, e.g. 600519,000858")):
    """mootdx TCP 五档盘口及实时价格"""
    symbol_list = symbols.split(",")
    return MarketService.get_mootdx_quotes(symbol_list)

@router.get("/market/transactions", tags=["Market"])
def get_transactions(code: str, date: Optional[str] = None):
    """mootdx TCP 逐笔成交记录"""
    return MarketService.get_mootdx_transactions(code, date)

@router.get("/market/tencent", tags=["Market"])
def get_tencent_quotes(symbols: str = Query(..., description="Comma separated tickers, e.g. 688017,300476")):
    """腾讯财经接口 - 极速实时估值（PE/PB/市值/换手率/涨跌停价）"""
    symbol_list = symbols.split(",")
    try:
        return MarketService.get_tencent_quotes(symbol_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/baidu", tags=["Market"])
def get_baidu_kline(code: str, start_time: Optional[str] = ""):
    """百度股市通 - 自带 MA5/10/20 均线的K线"""
    try:
        return MarketService.get_baidu_kline(code, start_time)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# LAYER 2: 研报层 (REPORTS)
# =====================================================================

@router.get("/reports/stock", tags=["Reports"])
def get_stock_reports(code: str, max_pages: int = 3):
    """东财个股研报列表"""
    return ReportsService.get_eastmoney_stock_reports(code, max_pages)

@router.get("/reports/industry", tags=["Reports"])
def get_industry_reports(industry_code: str = "*", max_pages: int = 3, begin: str = "2024-01-01"):
    """东财行业研报列表"""
    return ReportsService.get_eastmoney_industry_reports(industry_code, max_pages, begin)

@router.get("/reports/download", tags=["Reports"])
def download_pdf(info_code: str, title: str, org: str, date: str):
    """下载东财研报 PDF 文件，支持 Referer 限流防封"""
    try:
        pdf_path = ReportsService.download_report_pdf(info_code, title, org, date)
        return FileResponse(pdf_path, filename=f"{date}_{org}_{title}.pdf", media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/forecast", tags=["Reports"])
def get_consensus_forecast(code: str):
    """同花顺机构一致预期 (EPS Consensus)"""
    return ReportsService.get_ths_forecast(code)

@router.get("/reports/iwencai/search", tags=["Reports"])
def search_iwencai(query: str, channel: str = "report", size: int = 50):
    """iwencai NLP 语义搜索研报/公告/新闻 (需要 API Key)"""
    try:
        raw_results = ReportsService.search_iwencai(query, channel, size)
        if channel == "report":
            return ReportsService.dedup_articles(raw_results)
        return raw_results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports/iwencai/data", tags=["Reports"])
def query_iwencai_data(query: str, page: int = 1, limit: int = 50):
    """iwencai 结构化自然语言选股/财务查询 (需要 API Key)"""
    try:
        return ReportsService.query_iwencai_data(query, page, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =====================================================================
# LAYER 3: 信号层 (SIGNALS)
# =====================================================================

@router.get("/signals/hot", tags=["Signals"])
def get_ths_hot(date: Optional[str] = None):
    """同花顺当日最强龙头股归因 (人工运营题材标签)"""
    try:
        return SignalsService.get_ths_hot_reason(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/northbound", tags=["Signals"])
def get_northbound_flow():
    """北向资金实时累计分钟资金流向 (沪股通/深股通)"""
    try:
        return SignalsService.get_hsgt_realtime()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/blocks", tags=["Signals"])
def get_concept_blocks(code: str):
    """东财板块/概念板块归属 (行业/地域/概念、板块代码及龙头股)"""
    return SignalsService.get_eastmoney_concept_blocks(code)

@router.get("/signals/fundflow/minute", tags=["Signals"])
def get_fundflow_minute(code: str):
    """东财个股实时分钟级资金流向"""
    return SignalsService.get_eastmoney_fund_flow_minute(code)

@router.get("/signals/dragon-tiger", tags=["Signals"])
def get_dragon_tiger(code: str, date: str, look_back: int = 30):
    """个股近N日上榜原因、顶级营业部和机构席位资金净买额"""
    return SignalsService.get_dragon_tiger_board(code, date, look_back)

@router.get("/signals/lockup", tags=["Signals"])
def get_lockup_expiry(code: str, date: str, forward_days: int = 90):
    """限售解禁历史与未来 90 天待解禁预警日历"""
    return SignalsService.get_lockup_expiry(code, date, forward_days)

@router.get("/signals/industry-rank", tags=["Signals"])
def get_industry_rank(top_n: int = 20):
    """东财全行业涨跌、资金流主力流入及领涨个股监控"""
    return SignalsService.get_industry_comparison(top_n)

@router.get("/signals/daily-dragon-tiger", tags=["Signals"])
def get_daily_dragon_tiger(date: Optional[str] = None, min_net_buy: Optional[float] = None):
    """全市场当日所有触发龙虎榜的成交净额与换手排行榜"""
    return SignalsService.get_daily_dragon_tiger(date, min_net_buy)


# =====================================================================
# LAYER 4: 资金面/筹码层 (CAPITAL)
# =====================================================================

@router.get("/capital/margin", tags=["Capital"])
def get_margin(code: str, page_size: int = 30):
    """融资融券明细、融资余额变动、融券偿还指标"""
    return CapitalService.get_margin_trading(code, page_size)

@router.get("/capital/block-trade", tags=["Capital"])
def get_block_trade(code: str, page_size: int = 20):
    """大宗交易大额买卖双方营业部及溢折价排行"""
    return CapitalService.get_block_trade(code, page_size)

@router.get("/capital/holders", tags=["Capital"])
def get_holder_changes(code: str, page_size: int = 10):
    """最新披露季度股东户数、环比集中或发散指标"""
    return CapitalService.get_holder_num_change(code, page_size)

@router.get("/capital/dividends", tags=["Capital"])
def get_dividends(code: str, page_size: int = 20):
    """历史派红息方案、送股转增比例、现金派息实力"""
    return CapitalService.get_dividend_history(code, page_size)

@router.get("/capital/fundflow/120d", tags=["Capital"])
def get_fundflow_120d(code: str):
    """个股 120 日主力资金(超大/大单)净买入累积情况"""
    return CapitalService.get_stock_fund_flow_120d(code)


# =====================================================================
# LAYER 5: 新闻层 (NEWS)
# =====================================================================

@router.get("/news/stock", tags=["News"])
def get_stock_news(code: str, page_size: int = 20):
    """东财个股独有新闻资讯列表 (清除网页标签)"""
    return NewsService.get_eastmoney_stock_news(code, page_size)

@router.get("/news/global", tags=["News"])
def get_global_news(page_size: int = 50):
    """7x24小时财经快讯、全市场全球宏观电报流"""
    return NewsService.get_eastmoney_global_news(page_size)


# =====================================================================
# LAYER 6: 基础数据层 (FINANCIALS)
# =====================================================================

@router.get("/financials/mootdx", tags=["Financials"])
def get_mootdx_finance(code: str):
    """mootdx 季报 37 核心财务科目快照"""
    return FinancialsService.get_mootdx_finance(code)

@router.get("/financials/f10", tags=["Financials"])
def get_mootdx_f10(code: str, section: str = "公司概况"):
    """F10大项文本内容检索 (包括业内点评、行业分析等九大分类)"""
    return {"section": section, "content": FinancialsService.get_mootdx_f10(code, section)}

@router.get("/financials/stock-info", tags=["Financials"])
def get_stock_info(code: str):
    """东财基本股本结构、流通市值、行业分类与上市时间"""
    return FinancialsService.get_eastmoney_stock_info(code)

@router.get("/financials/sina", tags=["Financials"])
def get_sina_statements(code: str, type: str = "lrb", num: int = 8):
    """新浪披露三表：资产负债表 (fzb)、利润表 (lrb)、现金流量表 (llb)"""
    return FinancialsService.get_sina_financial_report(code, type, num)


# =====================================================================
# LAYER 7: 公告层 (ANNOUNCEMENTS)
# =====================================================================

@router.get("/announcements", tags=["Announcements"])
def get_announcements(code: str, page_size: int = 30):
    """巨潮资讯巨量公告检索，包含精确匹配的 orgId 转换及PDF路径"""
    return AnnouncementsService.get_cninfo_announcements(code, page_size)


# =====================================================================
# ADVANCED LAYER: 核心估值模型与投资评级
# =====================================================================

@router.get("/analysis/valuation", tags=["Analysis"])
def get_valuation_analysis(code: str):
    """
    高级财务估值引擎：
    1. 整合腾讯行情实时收盘价与总市值
    2. 同步同花顺一致预期 EPS 数据
    3. 运行前向 PE (Forward PE)、CAGR 业绩增长率、PEG 指标和 30x PE 消化时间
    """
    try:
        # 1. Fetch live price
        tencent_info = MarketService.get_tencent_quotes([code])
        if not tencent_info or code not in tencent_info:
            raise HTTPException(status_code=404, detail="Stock ticker not found in Tencent database")
        q = tencent_info[code]
        price = q["price"]
        pe_ttm = q["pe_ttm"]
        pb = q["pb"]
        mcap_yi = q["mcap_yi"]
        name = q["name"]
        
        # 2. Fetch Consensus Forecast
        forecast = ReportsService.get_ths_forecast(code)
        
        eps_cur = None
        eps_next = None
        analyst_count = 0
        
        if forecast and len(forecast) >= 2:
            try:
                # Based on typical THS forecast table rows
                row_cur = forecast[0]
                row_next = forecast[1]
                
                # Dynamic index retrieval (consensus values)
                for k, v in row_cur.items():
                    if "均值" in k or "收益" in k or "预测" in k:
                        try:
                            eps_cur = float(v)
                            break
                        except ValueError:
                            pass
                
                for k, v in row_next.items():
                    if "均值" in k or "收益" in k or "预测" in k:
                        try:
                            eps_next = float(v)
                            break
                        except ValueError:
                            pass
                            
                for k, v in row_cur.items():
                    if "机构" in k:
                        try:
                            analyst_count = int(v)
                            break
                        except ValueError:
                            pass
            except Exception:
                pass
                
        # 3. Valuation metrics processing
        pe_fwd = None
        cagr = 0.0
        peg = None
        digest_years = 0.0
        
        if eps_cur and eps_cur > 0:
            pe_fwd = price / eps_cur
            
            if eps_next and eps_next > eps_cur:
                cagr = (eps_next / eps_cur) - 1.0
                
            if cagr > 0:
                peg = pe_fwd / (cagr * 100)
                if pe_fwd > 30:
                    digest_years = math.log(pe_fwd / 30) / math.log(1.0 + cagr)
                    
        return {
            "code": code,
            "name": name,
            "price": price,
            "mcap_yi": mcap_yi,
            "pe_ttm": pe_ttm,
            "pb": pb,
            "analyst_count": analyst_count,
            "eps_forecast_cur": eps_cur,
            "eps_forecast_next": eps_next,
            "pe_forward": round(pe_fwd, 2) if pe_fwd else None,
            "cagr_percent": round(cagr * 100, 2),
            "peg": round(peg, 2) if peg else None,
            "pe_digestion_years_to_30x": round(digest_years, 2),
            "valuation_rating": (
                "UNDERVALUED (PEG < 1.0)" if peg and peg < 1.0 else
                "FAIR VALUE (PEG 1.0 - 1.5)" if peg and peg <= 1.5 else
                "OVERVALUED (PEG > 1.5)" if peg else "N/A (No analyst consensus)"
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation analysis calculation error: {e}")
