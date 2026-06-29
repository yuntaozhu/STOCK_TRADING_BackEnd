export interface EndpointInfo {
  method: string;
  path: string;
  desc: string;
  category: string;
  params: string;
}

export const BACKEND_ENDPOINTS: EndpointInfo[] = [
  // 行情层
  {
    method: "GET",
    path: "/api/market/tencent",
    desc: "腾讯财经极速实时行情及关键估值指标：同步读取实时价格、涨跌幅、最高/最低价、成交量/成交额，以及核心的 PE_ttm、PB 及流通/总市值。",
    category: "行情层 (Market)",
    params: "symbols (用逗号分隔的股票代码，例如: 688017,300476)",
  },
  {
    method: "GET",
    path: "/api/market/baidu",
    desc: "百度股市通 K线数据：获取多周期K线（日K/周K/月K等），内置自动清洗计算的 MA5、MA10、MA20 移动平均线指标。",
    category: "行情层 (Market)",
    params: "code (6位股票代码), start_time (可选起始时间)",
  },
  {
    method: "GET",
    path: "/api/market/kline",
    desc: "Mootdx TCP 直连原生 K线数据：通过极速 TCP 链路读取交易所原生高精度行情走势。",
    category: "行情层 (Market)",
    params: "code (6位代码), category (K线周期: 4=日K), offset (获取条数: 默认100)",
  },
  {
    method: "GET",
    path: "/api/market/quotes",
    desc: "Mootdx TCP 实时五档盘口及实时分笔价格：直连行情网关，监控买一到买五、卖一到卖五的高频量价变动。",
    category: "行情层 (Market)",
    params: "symbols (逗号分隔股票代码)",
  },
  {
    method: "GET",
    path: "/api/market/transactions",
    desc: "Mootdx TCP 历史逐笔成交流水：获取全天或历史单日详细的逐笔主动性买卖盘（主力吃单与散户吐单轨迹）。",
    category: "行情层 (Market)",
    params: "code (股票代码), date (可选特定日期 YYYYMMDD)",
  },

  // 研报层
  {
    method: "GET",
    path: "/api/reports/forecast",
    desc: "同花顺机构一致预期 (Consensus Estimates)：聚合全市场主流券商对个股未来三期（如 2025/2026/2027）的 EPS (每股收益) 的最大值、最小值、算术平均值，并提供研究机构覆盖数。",
    category: "研报层 (Reports)",
    params: "code (6位代码)",
  },
  {
    method: "GET",
    path: "/api/reports/stock",
    desc: "东方财富深度个股评级研报：实时爬取个股最新研报索引，包含评级调整（买入/增持/中性）、研报发布机构、发布日期等。",
    category: "研报层 (Reports)",
    params: "code (6位代码), max_pages (最大抓取页数: 默认3)",
  },
  {
    method: "GET",
    path: "/api/reports/industry",
    desc: "东方财富全行业深度研报检索：捕捉某一特定行业或全行业的深度跟踪研报，快速了解板块轮动与产业逻辑。",
    category: "研报层 (Reports)",
    params: "industry_code (可选行业代码, 默认*), max_pages (默认3), begin (起始时间)",
  },
  {
    method: "GET",
    path: "/api/reports/download",
    desc: "研报 PDF 原件安全中转下载：利用代理机制和 Referer 标头绕过东方财富研报服务器限流阻断，返回二进制 PDF 流，支持安全预览。",
    category: "研报层 (Reports)",
    params: "info_code (研报唯一ID), title (研报标题), org (研究机构), date (发布日期)",
  },
  {
    method: "GET",
    path: "/api/reports/iwencai/search",
    desc: "iWencai NLP 语义搜索引擎：使用自然语言搜索东方财富、同花顺研报/公告/新闻快讯，支持精准语义解析（需要 API Key）。",
    category: "研报层 (Reports)",
    params: "query (自然语言检索句), channel (渠道: 默认'report'), size (条数: 默认50)",
  },
  {
    method: "GET",
    path: "/api/reports/iwencai/data",
    desc: "iWencai 结构化自然语言智能选股与财务大表查询：支持极为复杂的语义选股规则（如: 昨收盘价大于30元且主力净买入前10且PEG小于1.2）（需要 API Key）。",
    category: "研报层 (Reports)",
    params: "query (自然语言选股条件), page (页码), limit (条数)",
  },

  // 信号层
  {
    method: "GET",
    path: "/api/signals/blocks",
    desc: "东方财富板块概念实时归属 (slist)：返回个股所属的东财概念板块、行业板块和地域板块，包括对应板块的代码、成分股总数及日内板块龙头股。",
    category: "信号层 (Signals)",
    params: "code (6位代码)",
  },
  {
    method: "GET",
    path: "/api/signals/hot",
    desc: "同花顺当日强势龙头题材与热点归因归纳：读取同花顺热点板块，提供当日最强的连板个股、涨停原因、归因标签（例如: '人形机器人+行星滚柱丝杠+特斯拉供应链'）。",
    category: "信号层 (Signals)",
    params: "date (可选日期 YYYY-MM-DD)",
  },
  {
    method: "GET",
    path: "/api/signals/northbound",
    desc: "北向资金 (沪股通/深股通) 实时累计分钟流向：监控外资日内分钟级的净流入/净流出曲线，是 A股 日内情绪极其灵敏的晴雨表。",
    category: "信号层 (Signals)",
    params: "无",
  },
  {
    method: "GET",
    path: "/api/signals/fundflow/minute",
    desc: "东方财富个股实时日内分钟级主力/超大单/大单/中单/散户资金净流向监控：直观判断日内异动是否属于大资金真实流入。",
    category: "信号层 (Signals)",
    params: "code (6位代码)",
  },
  {
    method: "GET",
    path: "/api/signals/dragon-tiger",
    desc: "个股历史龙虎榜明细：追踪个股近 N 天的上榜原因（如连续三日涨幅偏离20%）、顶级下游游资席位（如拉萨天团、呼家楼）和机构专用席位的大手笔净买入详情。",
    category: "信号层 (Signals)",
    params: "code (6位代码), date (截止日期), look_back (回溯天数: 默认30)",
  },
  {
    method: "GET",
    path: "/api/signals/lockup",
    desc: "限售股解禁预警日历：监控历史已解禁与未来 90 天待解禁股本结构、占总股本比重，防范突发式首发或定向增发解禁砸盘风险。",
    category: "信号层 (Signals)",
    params: "code (股票代码), date (基准日期), forward_days (向前预测天数: 默认90)",
  },
  {
    method: "GET",
    path: "/api/signals/industry-rank",
    desc: "东方财富全行业资金监控排行：按行业板块归纳，实时输出主力净流入前 20 行业以及行业内领涨的核心个股。",
    category: "信号层 (Signals)",
    params: "top_n (监控前N个行业: 默认20)",
  },
  {
    method: "GET",
    path: "/api/signals/daily-dragon-tiger",
    desc: "全市场每日最新龙虎榜合并快照：全市场当日上榜的所有个股，按游资净买入额、换手率等指标进行统一排名过滤。",
    category: "信号层 (Signals)",
    params: "date (可选特定日期), min_net_buy (过滤最低买入额)",
  },

  // 筹码与两融
  {
    method: "GET",
    path: "/api/capital/margin",
    desc: "融资融券基本面高维指标：获取每日详细的两融余额（融资余额、融券余额）、融资买入额、偿还额变动趋势，评估多空筹码博弈程度。",
    category: "筹码层 (Capital)",
    params: "code (6位代码), page_size (记录条数: 默认30)",
  },
  {
    method: "GET",
    path: "/api/capital/holders",
    desc: "最新季度股东户数增减与集中度：捕捉官方披露的最新季度末及历史中股东总户数的变动，并计算环比增减比例。股东户数大幅下降意味着“筹码急剧集中”，属于中线牛股标志性前兆。",
    category: "筹码层 (Capital)",
    params: "code (6位代码), page_size (默认10)",
  },
  {
    method: "GET",
    path: "/api/capital/dividends",
    desc: "个股历史分红方案与派息实力：历年详细的派息计划（如 10 派 5 元）、送股转增比例，评估企业现金分红的稳健度与股息率分红实力。",
    category: "筹码层 (Capital)",
    params: "code (6位代码), page_size (默认20)",
  },
  {
    method: "GET",
    path: "/api/capital/block-trade",
    desc: "大宗交易大额买卖记录：披露交易日内所有发生的大额溢价或折价交易，追踪买方/卖方营业部（如机构专用或特定游资总部）。",
    category: "筹码层 (Capital)",
    params: "code (6位代码), page_size (默认20)",
  },
  {
    method: "GET",
    path: "/api/capital/fundflow/120d",
    desc: "主力资金 120 日累计主力流向走势：对 120 个交易日以来的主力、超大单买入量进行累加，捕捉中长期长线资金吸筹期。",
    category: "筹码层 (Capital)",
    params: "code (6位代码)",
  },

  // 新闻公告层
  {
    method: "GET",
    path: "/api/news/stock",
    desc: "东方财富个股独占新闻：抓取并自动清洗 HTML 网页标签后的个股实时关联新闻快讯、媒体报道流。",
    category: "新闻层 (News)",
    params: "code (6位代码), page_size (默认20)",
  },
  {
    method: "GET",
    path: "/api/news/global",
    desc: "7x24 小时全天候全球宏观要闻电报流：覆盖全市场宏观事件、央行货币政策变动、国际金融市场波动及 A股 异动播报。",
    category: "新闻层 (News)",
    params: "page_size (默认50)",
  },
  {
    method: "GET",
    path: "/api/announcements",
    desc: "巨潮资讯官方披露个股监管公告：实时索引上交所、深交所、北交所上市公司发布的财报、董事会决议、股权变动等官方披露，附带一键极速 PDF 下载地址。",
    category: "公告层 (Announcements)",
    params: "code (6位代码), page_size (默认30)",
  },

  // 财务基础层
  {
    method: "GET",
    path: "/api/financials/mootdx",
    desc: "Mootdx 季报核心财务科目快照：提取 37 个包含总资产、净利润、营业收入、扣非净利润、现金及等价物在内的 A股 标准季度科目快照。",
    category: "财务层 (Financials)",
    params: "code (6位代码)",
  },
  {
    method: "GET",
    path: "/api/financials/f10",
    desc: "F10大项文本内容全文检索：包含公司概况、发行筹资、主要股东、业内点评、主营构成等九大硬核分类的文本数据。",
    category: "财务层 (Financials)",
    params: "code (6位代码), section (默认: 公司概况)",
  },
  {
    method: "GET",
    path: "/api/financials/stock-info",
    desc: "东方财富股本信息：获取总股本、流通股本、流通市值比例、核心所属行业分类、上市时间，用以精确测算流通筹码厚度。",
    category: "财务层 (Financials)",
    params: "code (6位代码)",
  },
  {
    method: "GET",
    path: "/api/financials/sina",
    desc: "新浪财经披露标准三表：提供未经压缩的最全资产负债表 (fzb)、利润表 (lrb)、现金流量表 (llb) 的历史多季度数据，完美对齐专业审计需求。",
    category: "财务层 (Financials)",
    params: "code (6位代码), type (fzb/lrb/llb), num (拉取季度数: 默认8)",
  },

  // 高级分析层
  {
    method: "GET",
    path: "/api/analysis/valuation",
    desc: "高级财务估值压力测试引擎：1. 自动同步腾讯行情实时价格。2. 同步同花顺机构未来三期一致预期 EPS 均值。3. 在后台构建运算模型，推演 Forward PE、EPS CAGR 业绩增长率、PEG 指标 and 消化到合理 PE (30x) 的待消化年数压力测试。4. 动态输出评级（UNDERVALUED/FAIR VALUE/OVERVALUED）。",
    category: "高级分析 (Analysis)",
    params: "code (6位代码)",
  }
];

export const STOCK_ANALYSIS_PROMPT = `# 🚀 A股 金融数据终端与 FastAPI 部署包集成开发提示词 (A-Share Financial Agent Prompt)

你是一个顶级量化金融分析师与全栈 AI 软件架构师。我们将使用一个高性能、支持 32 个数据端点的 **Python FastAPI 金融代理后端服务**，来构建一套交互式、专业极客范、采用社论美学设计的 **A股 个股多维智能透视与分析终端**。

---

## 💡 开发背景与设计原则 (Aesthetic & Vibe Guidelines)
1. **纸本社论美学 (Editorial Aesthetic)**:
   - **基础色调**：背景采用温暖纸张米白/暖灰色 (\`#FAF9F6\` 或 \`#F5F2EB\`)，高亮对比卡片使用深米色 (\`#EFECE8\`)。
   - **高强对比文字**：纯黑文字和深碳黑 (\`#1A1A1A\`)，杜绝轻飘飘的浅灰。
   - **经典墨线物理框**：所有容器卡片、按钮和输入框均配置粗实边框 (\`border-[1.5px] border-[#1A1A1A]\`) 并带有经典的像素偏移实心硬黑阴影 (\`shadow-[4px_4px_0px_#1A1A1A]\`)。
   - **排版节奏**：大标题与数值使用雅致的衬线字体 (如 Playfair Display / 乔治亚 / 宋体)，技术类指标与辅助标签使用等宽字体 (如 JetBrains Mono)。
2. **多维七层底座架构**: 
   - 股票透视分为七个层次：1. 基础行情与估值，2. 财务大表与盈利一致预期，3. 主力资金与筹码集中度，4. 实时新闻与公告追踪，5. 龙虎榜游资，6. 高级 PEG 估值与压力测试，7. 一键生成云原生部署包。
3. **安全代理策略**: 
   - 绝不暴露任何第三方金融 API 密钥到浏览器。前端必须统一调用此 FastAPI 服务提供的本地代理端点 (\`/api/*\`) 转发数据，后台支持多源混合解码（如腾讯财经的 GBK 极速解码及 Referer 避封策略）。

---

## 📋 完整的后端 API 接口文档 (Complete Backend API Reference)
后台共注册并集成了以下 32 个高价值 RESTful 金融数据端点，支持跨域、请求代理及 GBK 自动转码：

### 1. 行情与走势层 (Market Data API)
*   **\`GET /api/market/tencent\`**
    *   **描述**: 腾讯财经极速实时行情及关键估值指标（价格、涨跌幅、成交额、PE_ttm、PB及市值）。
    *   **参数**: \`symbols\` (用逗号分隔的股票代码，例如: \`688017,300476\`)
*   **\`GET /api/market/baidu\`**
    *   **描述**: 百度股市通 K线走势数据，自动清洗计算并集成 MA5, MA10, MA20 均线时序。
    *   **参数**: \`code\` (6位股票代码), \`start_time\` (可选起始时间)
*   **\`GET /api/market/kline\`**
    *   **描述**: Mootdx TCP 直连行情网关极速原生 K线数据（多周期支持，日K、周K等）。
    *   **参数**: \`code\` (6位代码), \`category\` (K线周期: 4=日K), \`offset\` (获取条数: 默认100)
*   **\`GET /api/market/quotes\`**
    *   **描述**: Mootdx TCP 实时五档盘口及即时价格监控，直连买一到买五、卖一到卖五高频深度。
    *   **参数**: \`symbols\` (用逗号分隔的股票代码)
*   **\`GET /api/market/transactions\`**
    *   **描述**: Mootdx TCP 历史逐笔成交流水，全天或特定交易日最精确的主动性买卖单分布。
    *   **参数**: \`code\` (6位股票代码), \`date\` (可选 YYYYMMDD 日期)

### 2. 机构研报与 NLP 智能检索 (Reports & NLP API)
*   **\`GET /api/reports/forecast\`**
    *   **描述**: 同花顺机构一致预期 (Consensus Estimates)，获取券商对未来三期个股每股收益 EPS 的极值与均值预期。
    *   **参数**: \`code\` (6位代码)
*   **\`GET /api/reports/stock\`**
    *   **描述**: 东方财富深度个股评级研报索引（包含评级调整、研报标题、研究机构、发布日期）。
    *   **参数**: \`code\` (6位代码), \`max_pages\` (爬取页数: 默认3)
*   **\`GET /api/reports/industry\`**
    *   **描述**: 东方财富全行业深度研报追踪，支持检索特定板块内的行业趋势研报。
    *   **参数**: \`industry_code\` (可选行业代码, 默认*), \`max_pages\` (默认3), \`begin\` (起始日期)
*   **\`GET /api/reports/download\`**
    *   **描述**: 研报 PDF 原件中转与安全下载代理，绕过服务器限流，支持前端直接预览 PDF 二进制流。
    *   **参数**: \`info_code\` (唯一ID), \`title\` (研报标题), \`org\` (机构), \`date\` (发布日期)
*   **\`GET /api/reports/iwencai/search\`**
    *   **描述**: 同花顺 iWencai NLP 语义搜索引擎，支持自然语言检索研报、公告与财经快讯（需要 API Key）。
    *   **参数**: \`query\` (自然语言搜索词), \`channel\` (默认'report'), \`size\` (条数: 默认50)
*   **\`GET /api/reports/iwencai/data\`**
    *   **描述**: 同花顺 iWencai 智能语义选股与财务大表多维查询，直接用自然语言过滤筛选个股（需要 API Key）。
    *   **参数**: \`query\` (语义选股条件), \`page\` (页码), \`limit\` (条数)

### 3. 主力信号与异动归因 (Signals & Theme Attribution)
*   **\`GET /api/signals/blocks\`**
    *   **描述**: 东方财富板块概念及行业归属实时映射，包含板块概念代码、龙头股名称与成分股数量。
    *   **参数**: \`code\` (6位代码)
*   **\`GET /api/signals/hot\`**
    *   **描述**: 同花顺每日强势题材风向标，提取当日盘面连板牛股涨停归因标签与题材共振逻辑。
    *   **参数**: \`date\` (可选 YYYY-MM-DD)
*   **\`GET /api/signals/northbound\`**
    *   **描述**: 沪港通、深港通（北向外资）实时盘中分钟级累计净买入额走势。
    *   **参数**: 无
*   **\`GET /api/signals/fundflow/minute\`**
    *   **描述**: 东方财富个股盘中主力/超大单/大单/中单/散户的分钟级多空搏弈实时资金流向。
    *   **参数**: \`code\` (6位代码)
*   **\`GET /api/signals/dragon-tiger\`**
    *   **描述**: 个股历史龙虎榜明细，包含上榜原因、顶级游资营业部席位买卖变动及机构专用席位净流入。
    *   **参数**: \`code\` (6位代码), \`date\` (截止日期), \`look_back\` (回溯天数: 默认30)
*   **\`GET /api/signals/lockup\`**
    *   **描述**: 限售股上市解禁预警日历，显示历史已解禁和未来 90 天待解禁股本数、占比及解禁类型。
    *   **参数**: \`code\` (6位代码), \`date\` (基准日期), \`forward_days\` (向前天数: 默认90)
*   **\`GET /api/signals/industry-rank\`**
    *   **描述**: 东方财富全行业实时主力资金净流入及龙头股领涨排行。
    *   **参数**: \`top_n\` (监控行业数: 默认20)
*   **\`GET /api/signals/daily-dragon-tiger\`**
    *   **描述**: 每日全市场最新的上榜个股龙虎榜合并快照与游资净买入额大排名。
    *   **参数**: \`date\` (可选特定日期), \`min_net_buy\` (过滤最低买入额)

### 4. 筹码集中度与杠杆平衡 (Capital & Leverage)
*   **\`GET /api/capital/margin\`**
    *   **描述**: 融资融券（两融）余额高频数据，获取融资买入、融券余量多空杠杆指标的每日变动。
    *   **参数**: \`code\` (6位代码), \`page_size\` (记录条数: 默认30)
*   **\`GET /api/capital/holders\`**
    *   **描述**: 最新季度末及历史股东总户数变动趋势，环比增减比例，用来挖掘“主力筹码急剧集中”信号。
    *   **参数**: \`code\` (6位代码), \`page_size\` (记录条数: 默认10)
*   **\`GET /api/capital/dividends\`**
    *   **描述**: 个股历年详细派息方案、送转比例、除权除息日等红利实力。
    *   **参数**: \`code\` (6位代码), \`page_size\` (默认20)
*   **\`GET /api/capital/block-trade\`**
    *   **描述**: 历史大宗交易大额非竞价买卖记录，监控买卖双方营业部和大额折溢价率。
    *   **参数**: \`code\` (6位代码), \`page_size\` (默认20)
*   **\`GET /api/capital/fundflow/120d\`**
    *   **描述**: 120 个交易日以来的累计主力、超大单大宗资金吸筹拉升走势。
    *   **参数**: \`code\` (6位代码)

### 5. 标准新闻与披露公告 (News & Disclosure)
*   **\`GET /api/news/stock\`**
    *   **描述**: 东方财富个股独占实时相关新闻流，经过去 HTML 文本清洗，提供纯净的文本媒体追踪。
    *   **参数**: \`code\` (6位代码), \`page_size\` (默认20)
*   **\`GET /api/news/global\`**
    *   **描述**: 7x24 全天候全球宏观要闻快讯、央行政策动向及 A股 热点实时推送。
    *   **参数**: \`page_size\` (默认50)
*   **\`GET /api/announcements\`**
    *   **描述**: 巨潮资讯权威上市公司公告索引，支持一键获取 PDF 下载与直链。
    *   **参数**: \`code\` (6位代码), \`page_size\` (默认30)

### 6. 专业财务基础三表与公司属性 (Financial Statements)
*   **\`GET /api/financials/mootdx\`**
    *   **描述**: Mootdx 高级 F10 财务指标，一键获取资产总额、扣非净利等 A股 37 个季度财务科目。
    *   **参数**: \`code\` (6位代码)
*   **\`GET /api/financials/f10\`**
    *   **描述**: 个股 F10 分类，包含公司概况、主营构成、主要股东等九大模块。
    *   **参数**: \`code\` (6位代码), \`section\` (默认: 公司概况)
*   **\`GET /api/financials/stock-info\`**
    *   **描述**: 东方财富最新股本信息（总股本、流通股本、流通占比），精密测量资金拉盘所需的市值厚度。
    *   **参数**: \`code\` (6位代码)
*   **\`GET /api/financials/sina\`**
    *   **描述**: 新浪财经标准财务三大报表原表（资产负债表 fzb、利润表 lrb、现金流量表 llb）历史多季度对齐。
    *   **参数**: \`code\` (6位代码), \`type\` (报表分类), \`num\` (拉取季度数)

### 7. 高级估值计算层 (Advanced Valuation & Valuation Pressure Test)
*   **\`GET /api/analysis/valuation\`**
    *   **描述**: 高级财务估值与PEG、PEG压力消化测试引擎。自动聚合当前实时价格与同花顺一致预期 EPS 进行核心量化公式演算，并得出评级结论。
    *   **参数**: \`code\` (6位代码)

---

## 🛠️ 数据路由对齐与前端绑定规范 (Data Route Bindings & UX)
在调用上述接口并开发股票透视分析终端时，请确保以下功能在前端完成：

1. **实时行情与K线走势**
   - **交互**: 顶端提供一个醒目的搜索框支持检索 6 位 A股 代码（如 \`688017\`, \`300476\`, \`600519\`）。
   - **实时五档**: 从 \`/api/market/tencent\` 及 \`/api/market/quotes\` 轮询最新交易价格、涨跌幅、最高/最低、盘口买卖五档变动。
   - **可视化**: 采用 Recharts 的 \`AreaChart\` 描绘由 \`/api/market/baidu\` 返回的 K线 价格走势，并在下方附带 MA5, MA10, MA20 的过滤复选开关，实现专业时序绘图。

2. **机构 Consensus EPS 预测与研报一键阅读**
   - **EPS 预测走势**: 从 \`/api/reports/forecast\` 中拉取机构未来三年对于每股盈余 EPS 的悲观、一致、乐观三层预测，使用 Recharts \`BarChart\` 进行立体并排展示。
   - **评级与 PDF 预览**: 读取 \`/api/reports/stock\` 的个股研报列表。列表里每行包含一个“在线查阅研报”按钮，在前端点击直接调用 \`/api/reports/download?info_code=...\` 获取二进制 PDF 研报并在 iframe 或新页面中完美浏览。

3. **主力资金、两融多空与筹码监控**
   - **资金多空**: 获取 \`/api/signals/fundflow/minute\`，提供主力/大单/中单/散户资金净流向监控，采用圆饼图（PieChart）或流向趋势展示。
   - **主力吸筹**: 抓取 \`/api/capital/holders\`，计算并展示几季度股东总户数的环比变化。如果股东户数连续下降，以粗墨线框或醒目色调高亮标注 **“筹码急剧集中，有主力资金中线潜伏！”**。
   - **两融杠杆**: 获取 \`/api/capital/margin\` 的融资融券数据，绘制多空博弈杠杆平衡走势。

4. **高级 PEG 估值与合理 PE 压力测试**
   - **核心算法展示**: 调用 \`/api/analysis/valuation?code={code}\`，并在前端清晰剖析算法并渲染：
     - *Forward PE* ($PE_{fwd} = P_0 / EPS_{cur}$)。
     - *EPS 增长率* ($CAGR = (EPS_{next} / EPS_{cur}) - 1$)。
     - *估值性价比 PEG* ($PEG = PE_{fwd} / (CAGR \\times 100)$)。
     - *估值消化至合理 PE (30.0x) 所需年限压力测试*：
       $$Y_{digest} = \frac{\ln(PE_{fwd} / 30)}{\ln(1.0 + CAGR)}$$
     - *动态评级* (UNDERVALUED: PEG < 1.0 | FAIR VALUE: PEG 1.0~1.5 | OVERVALUED: PEG > 1.5)。

---

## ⚡ 开发者实施路径与工程指令
- 请使用以上详尽的数据与美学定义，直接使用 **React 18 + Tailwind CSS** 或 **Vue 3 + Tailwind** 开发前端界面。
- 所有 API 调用，务必指向配置了 \`/api/proxy/*\` 或 \`/api/analysis/*\` 的 FastAPI 或 Node 本地路由，确保跨域安全和接口解析防封。
- 立即开始，输出符合上述高级规范的精美前端源代码！
`;
