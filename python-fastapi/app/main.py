import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings

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

# Custom performance profiling middleware — added before CORS so CORS runs outermost
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# CORSMiddleware must be added LAST so it is executed FIRST (FastAPI reverses middleware order).
# This ensures preflight OPTIONS requests are intercepted and responded to before any other
# middleware or route handler runs, preventing 502s on cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.superegoagent.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
    max_age=600,
)

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
def health_check():
    """
    Railway Healthcheck probe. Keeps the container active and monitors backend readiness.
    """
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# Bind our core api routers containing 28 modules and calculations
# Router import is deferred here (not at module level) to avoid blocking startup
# while heavy service dependencies are resolved. A fallback catch-all is registered
# if the import fails so the app still responds to healthchecks.
try:
    from app.routers.api import router as api_router
    app.include_router(api_router)
except Exception as e:
    print(f"Warning: Failed to import API router: {e}")
    from fastapi import APIRouter
    fallback_router = APIRouter()

    @fallback_router.get("/api/{path:path}", tags=["Fallback"])
    async def fallback(path: str):
        return {"error": "API router failed to load", "detail": str(e), "path": f"/api/{path}"}

    app.include_router(fallback_router)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 3000))
    # Run uvicorn on 0.0.0.0 to bind to all network interfaces
    uvicorn.run(app, host="0.0.0.0", port=port)

