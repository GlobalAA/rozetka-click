import asyncio

from aiohttp import web
from loguru import logger

from src.controller import (
    handle_add_proxy,
    handle_add_shop,
    handle_start,
    handle_status,
    handle_stop,
    handle_add_category,
    handle_get_categories,
    handle_get_proxies,
    handle_get_shops,
    handle_delete_shop,
    handle_delete_proxy,
    handle_delete_category,
)


def init_app() -> web.Application:
    app = web.Application()
    app["state"] = {"parser_task": None}
    app.router.add_post("/api/start", handle_start)
    app.router.add_post("/api/stop", handle_stop)
    app.router.add_get("/api/status", handle_status)
    app.router.add_post("/api/proxy", handle_add_proxy)
    app.router.add_post("/api/shop", handle_add_shop)
    app.router.add_get("/api/shops", handle_get_shops)
    app.router.add_get("/api/proxies", handle_get_proxies)
    app.router.add_get("/api/categories", handle_get_categories)
    app.router.add_post("/api/category", handle_add_category)
    app.router.add_delete("/api/shop/{shop_id}", handle_delete_shop)
    app.router.add_delete("/api/proxy/{proxy_id}", handle_delete_proxy)
    app.router.add_delete("/api/category/{category_id}", handle_delete_category)
    return app


if __name__ == "__main__":
    try:
        app = init_app()
        web.run_app(app, host="0.0.0.0", port=8080)
    except KeyboardInterrupt:
        logger.debug("Stopped by user")
