import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import axios from "axios";

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
      const dirPath = path.join(process.cwd(), "python-fastapi");
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

  // 4. INTEGRATE VITE FOR SPA CLIENT PREVIEW OR SERVE STATIC IN PRODUCTION
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Express server running on http://localhost:${PORT}`);
  });
}

startServer();
