import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_schema, conn_ctx
from .reference.seed import seed_all, bootstrap_ips, bootstrap_storage
from .routers import flows, storage, lng, demand, balance, meta, prices

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("gas-analytics")

app = FastAPI(title="gas-analytics", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(flows.router)
app.include_router(storage.router)
app.include_router(lng.router)
app.include_router(demand.router)
app.include_router(balance.router)
app.include_router(prices.router)


@app.on_event("startup")
def on_startup() -> None:
    init_schema()
    seed_all()
    with conn_ctx() as c:
        n_ips = c.execute("SELECT COUNT(*) FROM ip").fetchone()[0]
        n_fac = c.execute("SELECT COUNT(*) FROM storage_facility").fetchone()[0]
    if n_ips == 0:
        bootstrap_ips()
    if n_fac == 0:
        bootstrap_storage()
    from .config import settings
    if settings.log_level.upper() != "TEST":
        from .scheduler import start_scheduler
        start_scheduler()
    log.info("schema initialised, reference seeded, scheduler up")


@app.on_event("shutdown")
def on_shutdown() -> None:
    from .scheduler import stop_scheduler
    stop_scheduler()


@app.get("/")
def root():
    return {"name": "gas-analytics", "version": "0.1.0", "docs": "/docs"}


@app.get("/healthz")
def health():
    return {"ok": True}
