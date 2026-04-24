import asyncio
import time

from aiohttp import web
from loguru import logger
from playwright.async_api import ProxySettings

from src.database.repository import (add_proxy, create_category, create_shop,
                                     delete_category, delete_proxy,
                                     delete_shop, get_all_product_ids,
                                     get_categories, get_parser_status,
                                     get_proxies, get_shops, set_parser_status)
from src.parser.exceptions import DuplicateObjectError, RozetkaError
from src.parser.scraper import get_seller_products, process_category
from src.proxy import validate


async def start_parser(
    app: web.Application, iterations: int, delay_seconds: int = 0
) -> None:
    logger.debug("Start...")

    await set_parser_status(True)

    try:
        if delay_seconds > 0:
            logger.info(f"Delaying parser launch for {delay_seconds} seconds...")
            await asyncio.sleep(delay_seconds)

        proxies = await validate()
        if not proxies:
            logger.error("No valid proxies available after validation")
            return None

        first_proxy = proxies[0]

        # Build ProxySettings — Playwright natively supports username/password.
        proxy_settings: ProxySettings | None = ProxySettings(server=first_proxy.server)
        if first_proxy.username:
            proxy_settings["username"] = first_proxy.username
        if first_proxy.password:
            proxy_settings["password"] = first_proxy.password
        logger.info(f"Using proxy: {first_proxy.server}")

        # --- Stage 1: scan product lists ---
        shops_get = await get_shops()
        if not shops_get:
            logger.error("Not found shops")
            return None

        logger.info("Stage 1 — Scanning product list")
        await get_seller_products(shops_get, proxy=proxy_settings)
        logger.success("Stage 1 done — product list updated")

        # --- Stage 2: process categories ---
        categories = await get_categories()
        if not categories:
            logger.warning("No categories found, skipping process_category")
            return None

        all_products = await get_all_product_ids()
        logger.info(f"Loaded {len(all_products)} product IDs from DB")

        for i in range(iterations):
            logger.info(f"Stage 2 — Iteration {i + 1}/{iterations}")
            for category in categories:
                try:
                    await process_category(category, all_products, proxy=proxy_settings)
                except RozetkaError as e:
                    logger.error(
                        f"Error processing category {category.target_category}: {e}"
                    )
                    continue

    except asyncio.CancelledError:
        logger.warning("Parser task was abruptly cancelled")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in parser: {e}")
    finally:
        await set_parser_status(False)
        # Cancel scheduled stop if parser finished on its own
        if app.get("state"):
            state = app["state"]
            stop_task = state.get("stop_delay_task")
            if stop_task and not stop_task.done():
                stop_task.cancel()
            state["stop_delay_task"] = None
            state["stop_at"] = None
            if state.get("parser_task") is not None and state["parser_task"].done():
                state["parser_task"] = None


async def handle_start(request: web.Request) -> web.Response:
    state = request.app["state"]
    parser_task = state.get("parser_task")
    is_running = await get_parser_status()
    if is_running or (parser_task and not parser_task.done()):
        return web.json_response(
            {"status": "error", "message": "Parser is already running"}, status=400
        )

    try:
        data = await request.json()
        iterations = int(data.get("iterations", 1))
        delay_type = data.get("delay_type", "none")
        delay_value = data.get("delay_value", "")
    except Exception:
        iterations = 1
        delay_type = "none"
        delay_value = ""

    delay_seconds = 0
    if delay_type == "minutes":
        try:
            delay_seconds = int(float(delay_value) * 60)
        except ValueError:
            return web.json_response(
                {"status": "error", "message": "Invalid delay_value for 'minutes'"},
                status=400,
            )
    elif delay_type == "hours":
        try:
            delay_seconds = int(float(delay_value) * 3600)
        except ValueError:
            return web.json_response(
                {"status": "error", "message": "Invalid delay_value for 'hours'"},
                status=400,
            )
    elif delay_type == "exact_time":
        try:
            from datetime import datetime, timedelta

            now = datetime.now()
            target_time = datetime.strptime(delay_value, "%H:%M").time()
            target_dt = datetime.combine(now.date(), target_time)
            if target_dt < now:
                target_dt += timedelta(days=1)
            delay_seconds = int((target_dt - now).total_seconds())
        except ValueError:
            return web.json_response(
                {
                    "status": "error",
                    "message": "Invalid delay_value for 'exact_time', expected HH:MM",
                },
                status=400,
            )

    proxies = await get_proxies()
    if len(proxies) < 1:
        return web.json_response(
            {"status": "error", "message": "At least 1 proxy is required."},
            status=400,
        )

    shops = await get_shops()
    if not shops:
        return web.json_response(
            {"status": "error", "message": "At least 1 shop required"},
            status=400,
        )

    categories = await get_categories()
    if not categories:
        return web.json_response(
            {"status": "error", "message": "At least 1 category required"},
            status=400,
        )

    state["parser_task"] = asyncio.create_task(
        start_parser(request.app, iterations, delay_seconds)
    )
    return web.json_response({"status": "ok", "message": "Parser started"})


async def _stop_parser_now(app: web.Application) -> None:
    """Cancel the parser task and clear status."""
    state = app["state"]
    parser_task = state.get("parser_task")
    if parser_task and not parser_task.done():
        parser_task.cancel()
        state["parser_task"] = None
        await set_parser_status(False)
        logger.info("Parser stopped by scheduled stop task")
    else:
        is_running = await get_parser_status()
        if is_running:
            await set_parser_status(False)
            logger.info("Forced DB status to stopped by scheduled stop task")
    state["stop_at"] = None
    state["stop_delay_task"] = None


async def _stop_parser_delayed(app: web.Application, delay_seconds: int) -> None:
    try:
        logger.info(f"Scheduled stop in {delay_seconds} seconds...")
        await asyncio.sleep(delay_seconds)
        await _stop_parser_now(app)
    except asyncio.CancelledError:
        logger.info("Scheduled stop task was cancelled")
        raise


async def handle_stop(request: web.Request) -> web.Response:
    state = request.app["state"]

    # Parse optional delay from request body
    try:
        data = await request.json()
        delay_type = data.get("delay_type", "none")
        delay_value = data.get("delay_value", "")
    except Exception:
        delay_type = "none"
        delay_value = ""

    delay_seconds = 0
    if delay_type == "minutes":
        try:
            delay_seconds = int(float(delay_value) * 60)
        except ValueError:
            return web.json_response(
                {"status": "error", "message": "Invalid delay_value for 'minutes'"},
                status=400,
            )
    elif delay_type == "hours":
        try:
            delay_seconds = int(float(delay_value) * 3600)
        except ValueError:
            return web.json_response(
                {"status": "error", "message": "Invalid delay_value for 'hours'"},
                status=400,
            )
    elif delay_type == "exact_time":
        try:
            from datetime import datetime, timedelta

            now = datetime.now()
            target_time = datetime.strptime(delay_value, "%H:%M").time()
            target_dt = datetime.combine(now.date(), target_time)
            if target_dt < now:
                target_dt += timedelta(days=1)
            delay_seconds = int((target_dt - now).total_seconds())
        except ValueError:
            return web.json_response(
                {
                    "status": "error",
                    "message": "Invalid delay_value for 'exact_time', expected HH:MM",
                },
                status=400,
            )

    # Cancel any previously scheduled stop
    existing_stop = state.get("stop_delay_task")
    if existing_stop and not existing_stop.done():
        existing_stop.cancel()
        state["stop_delay_task"] = None

    if delay_seconds > 0:
        state["stop_at"] = time.time() + delay_seconds
        state["stop_delay_task"] = asyncio.create_task(
            _stop_parser_delayed(request.app, delay_seconds)
        )
        return web.json_response(
            {"status": "ok", "message": f"Parser will stop in {delay_seconds} seconds"}
        )

    # Immediate stop
    parser_task = state.get("parser_task")
    if parser_task and not parser_task.done():
        parser_task.cancel()
        state["parser_task"] = None
        await set_parser_status(False)
        return web.json_response({"status": "ok", "message": "Parser stopped"})

    is_running = await get_parser_status()
    if is_running:
        await set_parser_status(False)
        return web.json_response(
            {"status": "ok", "message": "Forced status to stopped in DB"}
        )

    return web.json_response(
        {"status": "error", "message": "Parser is not running"}, status=400
    )


async def handle_status(request: web.Request) -> web.Response:
    state = request.app["state"]
    is_running = await get_parser_status()
    stop_at = state.get("stop_at")
    return web.json_response({"running": is_running, "stop_at": stop_at})


async def handle_add_proxy(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        server = data["server"]
        username = data["username"]
        password = data["password"]
    except Exception:
        return web.json_response(
            {
                "status": "error",
                "message": "Invalid request parameters. Expected: server, username, password",
            },
            status=400,
        )

    proxies = await get_proxies()
    if len(proxies) >= 2:
        return web.json_response(
            {
                "status": "error",
                "message": "A maximum of 2 proxies is allowed. Delete an existing proxy first.",
            },
            status=400,
        )

    try:
        await add_proxy(server, username, password)
    except DuplicateObjectError as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

    return web.json_response({"status": "ok", "message": "Proxy added successfully"})


async def handle_add_shop(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        url = data["url"]
    except Exception:
        return web.json_response(
            {
                "status": "error",
                "message": "Invalid request parameters. Expected: url",
            },
            status=400,
        )

    try:
        shop_id = await create_shop(url)
    except DuplicateObjectError as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

    return web.json_response(
        {"status": "ok", "message": "Shop added successfully", "shop_id": shop_id}
    )


async def handle_get_shops(_: web.Request) -> web.Response:
    shops = await get_shops()
    data = [{"id": s.id, "url": s.url} for s in shops]
    return web.json_response({"status": "ok", "shops": data})


async def handle_get_proxies(_: web.Request) -> web.Response:
    proxies = await get_proxies()
    data = [{"id": p.id, "server": p.server, "username": p.username} for p in proxies]
    return web.json_response({"status": "ok", "proxies": data})


async def handle_get_categories(_: web.Request) -> web.Response:
    categories = await get_categories()
    data = [
        {
            "id": c.id,
            "target_product": c.target_product,
            "target_category": c.target_category,
        }
        for c in categories
    ]
    return web.json_response({"status": "ok", "categories": data})


async def handle_add_category(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        target_product = data["target_product"]
        target_category = data["target_category"]
    except Exception:
        return web.json_response(
            {
                "status": "error",
                "message": "Invalid request parameters. Expected: target_product, target_category",
            },
            status=400,
        )

    try:
        category_id = await create_category(target_product, target_category)
    except DuplicateObjectError as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

    return web.json_response(
        {
            "status": "ok",
            "message": "Category added successfully",
            "category_id": category_id,
        }
    )


async def handle_delete_shop(request: web.Request) -> web.Response:
    try:
        shop_id = int(request.match_info["shop_id"])
    except (KeyError, ValueError):
        return web.json_response(
            {"status": "error", "message": "Invalid shop_id"}, status=400
        )

    deleted = await delete_shop(shop_id)
    if deleted:
        return web.json_response({"status": "ok", "message": f"Shop {shop_id} deleted"})
    return web.json_response(
        {"status": "error", "message": "Shop not found"}, status=404
    )


async def handle_delete_proxy(request: web.Request) -> web.Response:
    try:
        proxy_id = int(request.match_info["proxy_id"])
    except (KeyError, ValueError):
        return web.json_response(
            {"status": "error", "message": "Invalid proxy_id"}, status=400
        )

    deleted = await delete_proxy(proxy_id)
    if deleted:
        return web.json_response(
            {"status": "ok", "message": f"Proxy {proxy_id} deleted"}
        )
    return web.json_response(
        {"status": "error", "message": "Proxy not found"}, status=404
    )


async def handle_delete_category(request: web.Request) -> web.Response:
    try:
        category_id = int(request.match_info["category_id"])
    except (KeyError, ValueError):
        return web.json_response(
            {"status": "error", "message": "Invalid category_id"}, status=400
        )

    deleted = await delete_category(category_id)
    if deleted:
        return web.json_response(
            {"status": "ok", "message": f"Category {category_id} deleted"}
        )
    return web.json_response(
        {"status": "error", "message": "Category not found"}, status=404
    )
