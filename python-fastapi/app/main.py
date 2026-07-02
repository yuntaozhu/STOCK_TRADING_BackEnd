import os
import sys
import time

# Dynamic sys.path inclusion to prevent ModuleNotFoundError in diverse deployment environments (like Railway, Docker, or Vercel)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers.api import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "基于 A股全栈数据工具包 (a-stock-data) 的高性能 Python FastAPI 接口服务。\n"
        "覆盖行情(mootdx+腾讯+百度K线)、研报(东财+同花顺+iwencai)、信号(同花顺热点+北向+龙虎榜+解禁+行业)、"
        "资金面(融资融券+大宗交易+股东户数+分红+资金流分钟级+资金流120日)、新闻(东财个股+全球资讯)、"
        "基础数据(mootdx财务/F10+东财+新浪三表)、公告(巨潮)七层数据源。"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure standard CORSMiddleware to allow requests from https://www.superegoagent.com, and local development/preview tools
# We dynamically pull origins from environment variables (like ALLOWED_ORIGINS, FRONTEND_URL, or APP_URL) for ultimate flexibility.
origins = [
    "https://www.superegoagent.com",
    "https://ais-dev-c3egle4pei5oenap2a4olb-21133040686.us-west2.run.app",
    "https://ais-pre-c3egle4pei5oenap2a4olb-21133040686.us-west2.run.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Read ALLOWED_ORIGINS env variable (supports comma-separated values)
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    for origin in allowed_origins_env.split(","):
        clean_origin = origin.strip()
        if clean_origin and clean_origin not in origins:
            origins.append(clean_origin)

# Read other common frontend/app URL env variables
for env_name in ["FRONTEND_URL", "APP_URL"]:
    val = os.environ.get(env_name, "")
    if val:
        clean_val = val.strip().rstrip("/")
        if clean_val and clean_val not in origins:
            origins.append(clean_val)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Custom performance profiling middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# General global exception handlers to make endpoints super resilient
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": 500,
            "message": "Internal Server Error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

@app.get("/", tags=["General"])
def read_root():
    """
    Service landing point. Returns welcome message and link to documentation.
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "documentation": "/docs",
        "redoc": "/redoc",
        "status": "online",
        "author": "Simon Lin (A-Stock-Data V3.2.3)"
    }

@app.get("/health", tags=["General"])
@app.get("/api/health", tags=["General"])
@app.get("/api/fastapi-health", tags=["General"])
def health_check():
    """
    Comprehensive health check probe. Supports Railway, local diagnostics, and frontend monitoring.
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

# Bind our core api routers containing 28 modules and calculations
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    import os
    port_str = os.environ.get("PORT", "3000")
    # Clean any non-digit characters just in case
    port_cleaned = "".join(c for c in port_str if c.isdigit())
    port = int(port_cleaned) if port_cleaned else 3000
    # Run uvicorn on 0.0.0.0 to bind to all network interfaces
    uvicorn.run(app, host="0.0.0.0", port=port)

