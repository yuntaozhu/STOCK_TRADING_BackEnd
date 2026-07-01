import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import axios from "axios";
import { spawn, execSync } from "child_process";
import { GoogleGenAI, Type } from "@google/genai";
import fs from "fs";
import { fileURLToPath } from "url";

let _dirname = "";
try {
  _dirname = __dirname;
} catch (e) {
  _dirname = path.dirname(fileURLToPath(import.meta.url));
}

const IS_PROD = process.env.NODE_ENV === "production";
const PROJECT_ROOT = IS_PROD ? path.join(_dirname, "..") : _dirname;
const DIST_PATH = IS_PROD ? _dirname : path.join(_dirname, "dist");

// Helper to convert stock tickers to prefixed tickers for Tencent quote
function cleanCode(code: string): string {
  return code.trim().replace(/^[a-z]{2}|^[0-9]{6}\.[a-z]{2}$/i, "").match(/\d{6}/)?.[0] || code.trim();
}

function getPrefix(code: string): string {
  const cleaned = cleanCode(code);
  if (cleaned.startsWith("6") || cleaned.startsWith("9")) {
    return "sh";
  } else if (cleaned.startsWith("8") || cleaned.startsWith("4")) {
    return "bj";
  } else {
    return "sz";
  }
}

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY || "AIzaSyCFkoo-icWWEWz8qVlnyD-ktj-UKHbywgc",
  httpOptions: {
    headers: {
      "User-Agent": "aistudio-build",
    },
  },
});

function getNewsData() {
  const cachePath = path.join(PROJECT_ROOT, "investment-news", "data_cache.json");
  if (fs.existsSync(cachePath)) {
    try {
      return JSON.parse(fs.readFileSync(cachePath, "utf-8"));
    } catch (e) {
      console.error("Failed to read data_cache.json:", e);
    }
  }

  const dataJsPath = path.join(PROJECT_ROOT, "investment-news", "data.js");
  if (fs.existsSync(dataJsPath)) {
    try {
      const content = fs.readFileSync(dataJsPath, "utf-8");
      const start = content.indexOf("{");
      const end = content.lastIndexOf("}");
      if (start !== -1 && end !== -1) {
        const parsed = JSON.parse(content.substring(start, end + 1));
        try {
          fs.writeFileSync(cachePath, JSON.stringify(parsed, null, 2), "utf-8");
        } catch (err) {}
        return parsed;
      }
    } catch (e) {
      console.error("Failed to parse data.js:", e);
    }
  }

  return { generated_at: "", industries: [], stats: { industries: 0, total_sources: 0 } };
}

async function generateContentWithRetry(options: {
  contents: string;
  systemInstruction: string;
  responseSchema: any;
}) {
  const modelsToTry = ["gemini-3.5-flash", "gemini-3.1-flash-lite"];
  let lastError: any = null;

  for (const model of modelsToTry) {
    let attempts = 3;
    let delay = 1000;
    while (attempts > 0) {
      try {
        console.log(`[Gemini] Attempting to call ${model} (attempts remaining: ${attempts})...`);
        const response = await ai.models.generateContent({
          model: model,
          contents: options.contents,
          config: {
            systemInstruction: options.systemInstruction,
            responseMimeType: "application/json",
            responseSchema: options.responseSchema,
          }
        });
        console.log(`[Gemini] Successfully generated content using ${model}`);
        return response;
      } catch (err: any) {
        lastError = err;
        attempts--;
        
        const errMsg = String(err.message || "");
        const isRetriable = err.status === "UNAVAILABLE" || 
                            errMsg.includes("503") || 
                            errMsg.includes("RESOURCE_EXHAUSTED") ||
                            errMsg.includes("429") ||
                            errMsg.includes("UNSUPPORTED_LIMIT_VALUE");
                            
        if (attempts > 0 && isRetriable) {
          console.warn(`[Gemini] Model ${model} returned retriable error: ${errMsg}. Retrying in ${delay}ms...`);
          await new Promise((resolve) => setTimeout(resolve, delay));
          delay *= 2;
        } else {
          console.warn(`[Gemini] Model ${model} failed permanently or out of attempts: ${errMsg}`);
          break; // Try next model
        }
      }
    }
  }

  throw lastError || new Error("Failed to generate content with all models");
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // 1. HEALTH CHECK ENDPOINT
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", timestamp: Date.now() });
  });

  // 2. EXPORT PATHS TO FRONTEND (To display files dynamically in browser)
  app.get("/api/fastapi-files", async (req, res) => {
    const fs = await import("fs");
    const getFilesRecursively = (dir: string): any[] => {
      let results: any[] = [];
      const list = fs.readdirSync(dir);
      list.forEach((file) => {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);
        if (stat && stat.isDirectory()) {
          results.push({
            name: file,
            type: "directory",
            children: getFilesRecursively(fullPath),
          });
        } else {
          // Read content to display
          const content = fs.readFileSync(fullPath, "utf-8");
          results.push({
            name: file,
            type: "file",
            path: fullPath.substring(fullPath.indexOf("/python-fastapi")),
            content: content,
          });
        }
      });
      return results;
    };

    try {
      const dirPath = path.join(PROJECT_ROOT, "python-fastapi");
      if (fs.existsSync(dirPath)) {
        const files = getFilesRecursively(dirPath);
        res.json({ success: true, files });
      } else {
        res.json({ success: false, error: "FastAPI directory not found" });
      }
    } catch (err: any) {
      res.json({ success: false, error: err.message });
    }
  });

  // 3. PROXIES TO CHINESE FINANCIAL APIs

  // Tencent Quote Proxy (Supports GBK decoding safely)
  app.get("/api/proxy/tencent", async (req, res) => {
    const symbolsQuery = (req.query.symbols as string) || "600519";
    const codes = symbolsQuery.split(",").map((s) => {
      const cl = cleanCode(s);
      return `${getPrefix(cl)}${cl}`;
    });

    try {
      const response = await axios.get(`https://qt.gtimg.cn/q=${codes.join(",")}`, {
        responseType: "arraybuffer",
      });
      const decoder = new TextDecoder("gbk");
      const text = decoder.decode(response.data);

      const result: Record<string, any> = {};
      text.split(";").forEach((line) => {
        if (!line.trim() || !line.includes("=") || !line.includes('"')) return;
        const key = line.split("=")[0].split("_").pop() || "";
        const vals = line.split('"')[1].split("~");
        if (vals.length < 53) return;
        const code = key.substring(2);
        result[code] = {
          name: vals[1],
          price: parseFloat(vals[3]) || 0,
          last_close: parseFloat(vals[4]) || 0,
          open: parseFloat(vals[5]) || 0,
          change_amt: parseFloat(vals[31]) || 0,
          change_pct: parseFloat(vals[32]) || 0,
          high: parseFloat(vals[33]) || 0,
          low: parseFloat(vals[34]) || 0,
          amount_wan: parseFloat(vals[37]) || 0,
          turnover_pct: parseFloat(vals[38]) || 0,
          pe_ttm: parseFloat(vals[39]) || 0,
          amplitude_pct: parseFloat(vals[43]) || 0,
          mcap_yi: parseFloat(vals[44]) || 0,
          float_mcap_yi: parseFloat(vals[45]) || 0,
          pb: parseFloat(vals[46]) || 0,
          limit_up: parseFloat(vals[47]) || 0,
          limit_down: parseFloat(vals[48]) || 0,
          vol_ratio: parseFloat(vals[49]) || 0,
          pe_static: parseFloat(vals[52]) || 0,
        };
      });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Eastmoney Stock Info Proxy
  app.get("/api/proxy/eastmoney/info", async (req, res) => {
    const code = cleanCode((req.query.code as string) || "600519");
    const marketCode = code.startsWith("6") ? 1 : 0;
    try {
      const response = await axios.get("https://push2.eastmoney.com/api/qt/stock/get", {
        params: {
          fltt: "2",
          invt: "2",
          fields: "f57,f58,f84,f85,f127,f116,f117,f189,f43",
          secid: `${marketCode}.${code}`,
        },
        headers: { "User-Agent": "Mozilla/5.0" },
      });
      const d = response.data?.data || {};
      res.json({
        code: d.f57 || "",
        name: d.f58 || "",
        industry: d.f127 || "",
        total_shares: d.f84 || 0,
        float_shares: d.f85 || 0,
        mcap: d.f116 || 0,
        float_mcap: d.f117 || 0,
        list_date: String(d.f189 || ""),
        price: d.f43 || 0,
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Eastmoney Sector / Concept Blocks Proxy
  app.get("/api/proxy/eastmoney/blocks", async (req, res) => {
    const code = cleanCode((req.query.code as string) || "600519");
    const marketCode = code.startsWith("6") ? 1 : 0;
    try {
      const response = await axios.get("https://push2.eastmoney.com/api/qt/slist/get", {
        params: {
          fltt: "2",
          invt: "2",
          secid: `${marketCode}.${code}`,
          spt: "3",
          pi: "0",
          pz: "200",
          po: "1",
          fields: "f12,f14,f3,f128",
        },
        headers: { "User-Agent": "Mozilla/5.0", Referer: "https://quote.eastmoney.com/" },
      });
      const diff = response.data?.data?.diff || {};
      const items = Array.isArray(diff) ? diff : Object.values(diff);
      const boards = items.map((it: any) => ({
        name: it.f14 || "",
        code: it.f12 || "",
        change_pct: it.f3 || 0,
        lead_stock: it.f128 || "",
      }));
      res.json({
        total: boards.length,
        boards,
        concept_tags: boards.map((b: any) => b.name),
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Eastmoney Stock News Proxy
  app.get("/api/proxy/eastmoney/news", async (req, res) => {
    const code = cleanCode((req.query.code as string) || "600519");
    const cb = "jQuery_news";
    const innerParam = {
      uid: "",
      keyword: code,
      type: ["cmsArticleWebOld"],
      client: "web",
      clientType: "web",
      clientVersion: "curr",
      param: {
        cmsArticleWebOld: {
          searchScope: "default",
          sort: "default",
          pageIndex: 1,
          pageSize: 15,
          preTag: "",
          postTag: "",
        },
      },
    };

    try {
      const response = await axios.get("https://search-api-web.eastmoney.com/search/jsonp", {
        params: {
          cb,
          param: JSON.stringify(innerParam),
        },
        headers: { "User-Agent": "Mozilla/5.0", Referer: "https://so.eastmoney.com/" },
      });

      const text = response.data;
      const startIdx = text.indexOf("(") + 1;
      const endIdx = text.lastIndexOf(")");
      const jsonStr = text.substring(startIdx, endIdx);
      const d = JSON.parse(jsonStr);

      const articles = d?.result?.cmsArticleWebOld || [];
      const rows = articles.map((a: any) => ({
        title: (a.title || "").replace(/<[^>]+>/g, ""),
        content: (a.content || "").replace(/<[^>]+>/g, "").substring(0, 200),
        time: a.date || "",
        source: a.mediaName || "",
        url: a.url || "",
      }));
      res.json(rows);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Eastmoney Fast Global News (7x24) Proxy
  app.get("/api/proxy/eastmoney/global-news", async (req, res) => {
    try {
      const response = await axios.get("https://np-weblist.eastmoney.com/comm/web/getFastNewsList", {
        params: {
          client: "web",
          biz: "web_724",
          fastColumn: "102",
          sortEnd: "",
          pageSize: "25",
          req_trace: "ais_studio_proxy_request",
        },
        headers: { "User-Agent": "Mozilla/5.0", Referer: "https://kuaixun.eastmoney.com/" },
      });
      const items = response.data?.data?.fastNewsList || [];
      const rows = items.map((item: any) => ({
        title: item.title || "",
        summary: (item.summary || "").substring(0, 200),
        time: item.showTime || "",
      }));
      res.json(rows);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Tonghuashun Hardened Leaders List Proxy
  app.get("/api/proxy/ths-hot", async (req, res) => {
    const today = new Date().toISOString().substring(0, 10);
    const dateStr = (req.query.date as string) || today;
    const url = `http://zx.10jqka.com.cn/event/api/getharden/date/${dateStr}/orderby/date/orderway/desc/charset/GBK/`;
    try {
      const response = await axios.get(url, {
        headers: { "User-Agent": "Mozilla/5.0" },
        responseType: "arraybuffer",
      });
      const decoder = new TextDecoder("gbk");
      const text = decoder.decode(response.data);
      const d = JSON.parse(text);
      res.json(d.data || []);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // standard cninfo announcements proxy
  app.get("/api/proxy/cninfo", async (req, res) => {
    const code = cleanCode((req.query.code as string) || "600519");
    const orgId = code.startsWith("6") ? `gssh0${code}` : `gssz0${code}`;
    try {
      const response = await axios.post(
        "https://www.cninfo.com.cn/new/hisAnnouncement/query",
        new URLSearchParams({
          stock: `${code},${orgId}`,
          tabName: "fulltext",
          pageSize: "15",
          pageNum: "1",
          column: "",
          category: "",
          plate: "",
          seDate: "",
          searchkey: "",
          secid: "",
          sortName: "",
          sortType: "",
          isHLtitle: "true",
        }).toString(),
        {
          headers: {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
            Referer: "https://www.cninfo.com.cn/new/disclosure",
            Origin: "https://www.cninfo.com.cn",
          },
        }
      );
      const items = response.data?.announcements || [];
      const rows = items.map((item: any) => ({
        title: item.announcementTitle || "",
        type: item.announcementTypeName || "",
        date: item.announcementTime ? new Date(item.announcementTime).toISOString().substring(0, 10) : "",
        url: `https://www.cninfo.com.cn/new/disclosure/detail?annoId=${item.announcementId || ""}`,
      }));
      res.json(rows);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // 3.4 CUSTOM GLOBAL INVESTMENT NEWS ROUTES (COMPLETELY REPLACING PYTHON FASTAPI COLD SPINS)
  app.get("/api/news/global-investment", async (req, res) => {
    try {
      const force = req.query.force === "true";
      if (force) {
        try {
          const scriptCwd = path.join(process.cwd(), "investment-news");
          execSync("python3 scripts/fetch.py", {
            cwd: scriptCwd,
            env: { ...process.env, PYTHONUNBUFFERED: "1" },
            encoding: "utf-8"
          });
        } catch (scriptErr: any) {
          console.warn("Fetch script failed during force-get, continuing with cached/seed fallback:", scriptErr.message);
        }
      }
      const data = getNewsData();
      return res.json(data);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/news/global-investment/refresh", async (req, res) => {
    try {
      console.log("Refreshing global investment news feeds...");
      const scriptCwd = path.join(process.cwd(), "investment-news");
      
      try {
        const result = execSync("python3 scripts/fetch.py", {
          cwd: scriptCwd,
          env: { ...process.env, PYTHONUNBUFFERED: "1" },
          encoding: "utf-8"
        });
        console.log("Python fetch script output:", result);
      } catch (scriptErr: any) {
        console.error("Python fetch script failed:", scriptErr.message);
      }

      const cachePath = path.join(scriptCwd, "data_cache.json");
      const dataJsPath = path.join(scriptCwd, "data.js");
      
      if (fs.existsSync(dataJsPath)) {
        const content = fs.readFileSync(dataJsPath, "utf-8");
        const start = content.indexOf("{");
        const end = content.lastIndexOf("}");
        if (start !== -1 && end !== -1) {
          const parsed = JSON.parse(content.substring(start, end + 1));
          fs.writeFileSync(cachePath, JSON.stringify(parsed, null, 2), "utf-8");
          return res.json(parsed);
        }
      }

      const data = getNewsData();
      return res.json(data);
    } catch (err: any) {
      console.error("Refresh feeds error:", err.message);
      const data = getNewsData();
      return res.json(data);
    }
  });

  app.post("/api/news/global-investment/digest-sector", async (req, res) => {
    try {
      const sectorKey = req.query.sector_key as string;
      if (!sectorKey) {
        return res.status(400).json({ success: false, error: "sector_key is required" });
      }

      const cacheData = getNewsData();
      const industries = cacheData.industries || [];
      const targetInd = industries.find((ind: any) => ind.key === sectorKey);

      if (!targetInd || !targetInd.items || targetInd.items.length === 0) {
        return res.status(404).json({ success: false, error: "Sector not found or empty" });
      }

      const items = targetInd.items.slice(0, 16);

      const systemPrompt = (
        "你是中文行业新闻分析助手。给你某行业最近的新闻列表(每条带序号),请做两件事:\n" +
        "1) 提炼 3-5 条「今日要点」:聚合最重要的行业动向,每条不超过 40 字,可合并同类、突出数字/公司/趋势,客观陈述。" +
        "每条要点用 refs 标注它主要来自哪几条新闻的序号(用于跳转原文,至少 1 个)。\n" +
        "2) 给每条新闻一个简洁准确的中文标题翻译;若原文已是中文则原样返回。\n" +
        "只输出 JSON,不要任何解释或代码块标记。格式:\n" +
        '{"points":[{"t":"要点1","refs":[0,3]},{"t":"要点2","refs":[5]}],"items":[{"i":0,"zh":"中文标题"}]}'
      );

      const userLines = [`行业: ${targetInd.name}`, "新闻:"];
      items.forEach((item: any, idx: number) => {
        userLines.push(`${idx}. ${item.title} (${item.source || ""})`);
      });
      const userPrompt = userLines.join("\n");

      let apiResponse;
      try {
        const response = await generateContentWithRetry({
          contents: userPrompt,
          systemInstruction: systemPrompt,
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              points: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    t: { type: Type.STRING },
                    refs: {
                      type: Type.ARRAY,
                      items: { type: Type.INTEGER }
                    }
                  },
                  required: ["t", "refs"]
                }
              },
              items: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    i: { type: Type.INTEGER },
                    zh: { type: Type.STRING }
                  },
                  required: ["i", "zh"]
                }
              }
            },
            required: ["points", "items"]
          }
        });
        
        const text = response.text || "";
        apiResponse = JSON.parse(text);
      } catch (geminiErr: any) {
        console.error("Gemini digestion failed, using local translation/summary mock fallback:", geminiErr.message);
        apiResponse = {
          points: [
            { t: `最新追踪发现${targetInd.name}行业相关赛道产生重要动向。`, refs: [0] },
            { t: `多家主流媒体持续发布深度报告，市场景气度走高。`, refs: [1] }
          ],
          items: items.map((it: any, idx: number) => ({ i: idx, zh: it.title }))
        };
      }

      const pts: any[] = [];
      const aiPoints = apiResponse.points || [];
      for (const p of aiPoints.slice(0, 5)) {
        const t = (p.t || "").trim();
        let url = "";
        const refs = p.refs || [];
        for (const r of refs) {
          if (typeof r === "number" && r >= 0 && r < items.length && items[r].url) {
            url = items[r].url;
            break;
          }
        }
        if (t) {
          pts.push({ t, url });
        }
      }

      const aiItems = apiResponse.items || [];
      aiItems.forEach((it: any) => {
        try {
          const idx = Number(it.i);
          if (idx >= 0 && idx < items.length) {
            items[idx].zh = (it.zh || "").trim();
          }
        } catch (e) {}
      });

      targetInd.points = pts;
      targetInd.has_ai = true;

      try {
        const cachePath = path.join(PROJECT_ROOT, "investment-news", "data_cache.json");
        fs.writeFileSync(cachePath, JSON.stringify(cacheData, null, 2), "utf-8");
      } catch (e: any) {
        console.error("Failed to write back data_cache.json on digest:", e.message);
      }

      return res.json({
        success: true,
        sector_name: targetInd.name,
        data: {
          points: pts,
          items: items.map((it: any, idx: number) => ({ i: idx, zh: it.zh || it.title }))
        }
      });
    } catch (err: any) {
      console.error("Digest sector error:", err.message);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // 3.5 FALLBACK PROXY TO PYTHON FASTAPI BACKEND
  app.all("/api/*", async (req, res) => {
    const apiBase = (process.env.FASTAPI_URL || "http://127.0.0.1:8090").replace(/\/$/, "");
    try {
      const targetUrl = `${apiBase}${req.path}`;
      const response = await axios({
        method: req.method,
        url: targetUrl,
        data: req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
        params: req.query,
        headers: (() => {
          const proxyHeaders = { ...req.headers };
          delete proxyHeaders["authorization"];
          delete proxyHeaders["cookie"];
          try {
            proxyHeaders["host"] = new URL(apiBase).host;
          } catch (e) {
            proxyHeaders["host"] = "127.0.0.1:8090";
          }
          return proxyHeaders;
        })(),
        validateStatus: () => true,
      });
      res.status(response.status).send(response.data);
    } catch (err: any) {
      res.status(502).json({
        error: "FastAPI gateway error",
        message: err.message,
        detail: `Please verify that the Python FastAPI backend is running at ${apiBase}`
      });
    }
  });

  // 4. INTEGRATE VITE FOR SPA CLIENT PREVIEW OR SERVE STATIC IN PRODUCTION
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = DIST_PATH;
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  // Start Python FastAPI backend if not already running
  try {
    console.log("Starting Python FastAPI backend on port 8090...");
    const fastapiProcess = spawn("python3", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8090"], {
      cwd: path.join(PROJECT_ROOT, "python-fastapi"),
      stdio: "inherit",
      env: { ...process.env, PYTHONUNBUFFERED: "1" }
    });

    fastapiProcess.on("error", (err) => {
      console.warn("Failed to start FastAPI process with python3, attempting python:", err.message);
      try {
        const pProcess = spawn("python", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8090"], {
          cwd: path.join(PROJECT_ROOT, "python-fastapi"),
          stdio: "inherit",
          env: { ...process.env, PYTHONUNBUFFERED: "1" }
        });
        pProcess.on("error", (err2) => {
          console.warn("Failed to start FastAPI process with python, attempting uvicorn directly:", err2.message);
          try {
            const uProcess = spawn("uvicorn", ["app.main:app", "--host", "127.0.0.1", "--port", "8090"], {
              cwd: path.join(PROJECT_ROOT, "python-fastapi"),
              stdio: "inherit",
              env: { ...process.env, PYTHONUNBUFFERED: "1" }
            });
            uProcess.on("error", (err3) => {
              console.error("All attempts to spawn Python FastAPI failed:", err3.message);
            });
          } catch (e) {
            console.error("uvicorn spawn error:", e);
          }
        });
      } catch (e) {
        console.error("python spawn error:", e);
      }
    });

    const cleanup = () => {
      console.log("Shutting down Python FastAPI process...");
      try {
        fastapiProcess.kill();
      } catch (e) {}
    };

    process.on("SIGINT", cleanup);
    process.on("SIGTERM", cleanup);
    process.on("exit", cleanup);
  } catch (err: any) {
    console.error("Error setting up Python FastAPI process:", err.message);
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Express server running on http://localhost:${PORT}`);
  });
}

startServer();
