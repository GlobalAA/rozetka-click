import asyncio
import os
import shutil
from collections.abc import Sequence
from contextlib import asynccontextmanager
from random import uniform

from loguru import logger
from playwright.async_api import (BrowserContext, Error as PlaywrightError,
                                  Page, Playwright, ProxySettings, async_playwright)

from src.config import config
from src.database.models import Category, Shop
from src.database.repository import create_product, delete_products, get_shops
from src.parser.exceptions import (AdvertisementBlockNotFoundError,
                                   BoundingBoxError,
                                   ProductCardsNotFoundError,
                                   ProductsListEmptyError,
                                   TargetProductNotFoundError)


_RETRYABLE_ERRORS = (
    "ERR_EMPTY_RESPONSE",
    "ERR_CONNECTION_RESET",
    "ERR_CONNECTION_REFUSED",
    "ERR_NAME_NOT_RESOLVED",
    "ERR_TIMED_OUT",
    "NS_ERROR_NET_INTERRUPT",
    "Timeout",
)
_MAX_RETRIES = 4
_RETRY_BASE_DELAY = 5.0  # seconds, doubles each attempt


async def _goto_with_retry(page: Page, url: str, **kwargs) -> object:
    """Navigate to *url* retrying on transient network errors."""
    delay = _RETRY_BASE_DELAY
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await page.goto(url, **kwargs)
        except PlaywrightError as exc:
            if not any(err in str(exc) for err in _RETRYABLE_ERRORS):
                raise
            last_exc = exc
            logger.warning(
                f"[goto retry {attempt}/{_MAX_RETRIES}] {exc.message!r} — "
                f"waiting {delay:.0f}s before retry… (url={url})"
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
    raise last_exc  # type: ignore[misc]


def _is_test_proxy(proxy: ProxySettings | None) -> bool:
    """Returns True for test proxies (test://test:90...) that bypass the forwarder."""
    if proxy is None:
        return False
    server: str = proxy.get("server", "")  # type: ignore[union-attr]
    return server.startswith("test://")


@asynccontextmanager
async def _browser_session(proxy: ProxySettings | None):
    """
    Open a fresh persistent browser context with the given proxy, yield it,
    then close the context and stop Playwright.

    Test proxies (test://) are passed directly to the browser without a forwarder.
    """
    if os.path.exists(config.PROFILE_PATH):
        try:
            shutil.rmtree(config.PROFILE_PATH)
            logger.info("Cleared browser profile data (Cookies, LocalStorage, etc.)")
        except Exception as e:
            logger.warning(f"Failed to clear browser profile data: {e}")

    playwright: Playwright = await async_playwright().start()
    try:
        launch_args: dict = {
            "user_data_dir": config.PROFILE_PATH,
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if proxy is not None and not _is_test_proxy(proxy):
            launch_args["proxy"] = proxy

        context: BrowserContext = await playwright.chromium.launch_persistent_context(**launch_args)
        context.set_default_timeout(60_000)
        context.set_default_navigation_timeout(90_000)
        try:
            yield context
        finally:
            await context.close()
    finally:
        await playwright.stop()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_seller_products(
    shops: Sequence[Shop],
    proxy: ProxySettings | None = None,
) -> Sequence[Shop]:
    """
    Open browser → scan each shop's product list → close browser.
    Returns the updated list of shops from the DB.
    """
    logger.info("Opening browser for get_seller_products")
    async with _browser_session(proxy) as context:
        page = await context.new_page()
        worker = RozetkaWorker()

        try:
            for shop in shops:
                shop_url = shop.url
                await delete_products(shop_url)

                stop = False
                page_num = 1

                while not stop:
                    url = f"{shop_url}?page={page_num}" if page_num > 1 else shop_url
                    response = await _goto_with_retry(page, url)
                    if response and response.url != url:
                        break

                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_selector("a.tile-title")

                    urls = await worker.get_products(page)
                    if not urls:
                        stop = True
                        break

                    for product in urls:
                        await create_product(product.split("/")[-2], shop.id)

                    page_num += 1
                    await asyncio.sleep(uniform(2, 6))

                await asyncio.sleep(uniform(3, 7))
        finally:
            await page.close()

    logger.info("Browser closed after get_seller_products")
    return await get_shops()


async def process_category(
    category: Category,
    products: set[str],
    proxy: ProxySettings | None = None,
) -> bool:
    """
    Open browser → click target product → process advertisements → close browser.
    """
    logger.info(f"Opening browser for process_category: {category.target_category}")
    async with _browser_session(proxy) as context:
        page = await context.new_page()
        worker = RozetkaWorker()

        try:
            await worker.click_target_product(page, category)
            await worker.process_adv(page, products)
        finally:
            await page.close()

    logger.info("Browser closed after process_category")
    return True


# ---------------------------------------------------------------------------
# Worker (page-level logic only — no browser lifecycle)
# ---------------------------------------------------------------------------

class RozetkaWorker:

    async def get_products(self, page: Page) -> list[str] | None:
        urls = await page.query_selector_all("a.tile-title")
        products: list[str] = []

        for url in urls:
            href = await url.get_attribute("href")
            if not href:
                continue
            products.append(href)

        if len(products) == 0:
            raise ProductCardsNotFoundError(
                f"Product cards not found on page: {page.url}"
            )

        return products

    async def click_target_product(self, page: Page, category: Category) -> bool:
        await _goto_with_retry(page, category.target_category)
        await page.wait_for_load_state("domcontentloaded")

        urls = await self.get_products(page)

        if not urls:
            raise ProductsListEmptyError(
                f"Products list is empty for category URL: {category.target_category}"
            )

        if category.target_product not in urls:
            raise TargetProductNotFoundError(
                f"Target product URL '{category.target_product}' not found "
                f"in category '{category.target_category}'"
            )

        index = urls.index(category.target_product)
        await _goto_with_retry(page, urls[index])
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1.525)

        return True

    async def process_adv(self, page: Page, products: set[str]) -> bool:
        await page.wait_for_load_state("networkidle", timeout=60000)
        await page.wait_for_selector(".h2.pe-2")

        adv_block = await page.query_selector(
            ".primacy-slider-theme.d-block.mt-2.bg-white.rounded-2.p-4"
            "[data-testid='primacy-slider'] > rz-scroller > .wrap",
            strict=True,
        )

        if not adv_block:
            raise AdvertisementBlockNotFoundError(
                f"Advertisement block not found on the page: {page.url}"
            )

        await adv_block.scroll_into_view_if_needed()

        adv_block_box = await adv_block.bounding_box()
        if not adv_block_box:
            raise BoundingBoxError(
                f"Failed to get bounding box for the advertisement block on page: {page.url}"
            )

        center_x = adv_block_box["x"] + adv_block_box["width"] / 2
        center_y = adv_block_box["y"] + adv_block_box["height"] / 2

        await page.mouse.move(center_x, center_y)

        for _ in range(20):
            await page.mouse.wheel(+200, 0)
            await asyncio.sleep(0.016)

        with_ptoken = await page.query_selector_all("a.text-base[href*='primacyToken']")

        for ptoken in with_ptoken:
            href = await ptoken.get_attribute("href")
            if not href:
                logger.warning(
                    f"Attribute 'href' is missing for primacyToken element: {ptoken}"
                )
                continue

            product_id = href.split("/")[-2]

            if product_id in products:
                new_page = await page.context.new_page()
                await new_page.goto(href)
                await new_page.wait_for_load_state("networkidle", timeout=60000)
                await asyncio.sleep(uniform(1, 4))
                await new_page.close()

        return True
