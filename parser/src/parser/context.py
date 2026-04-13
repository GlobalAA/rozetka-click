from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar, cast

from playwright.async_api import BrowserContext, Page, ProxySettings

from src.parser.exceptions import BrowserNotInitializedError

P = ParamSpec("P")
R = TypeVar("R")


@asynccontextmanager
async def browser_page(context: BrowserContext):
    page = await context.new_page()
    try:
        yield page
    finally:
        await page.close()


def with_page(
    fn: Callable[Concatenate[Any, Page, P], Coroutine[Any, Any, R]],
) -> Callable[Concatenate[Any, P], Coroutine[Any, Any, R | None]]:
    @wraps(fn)
    async def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> R | None:
        if not self.browser or not self.context:
            raise BrowserNotInitializedError("Not found browser or context")

        proxy: ProxySettings | None = cast(
            ProxySettings | None, kwargs.pop("proxy", None)
        )
        server = proxy.get("server", None) if proxy is not None else None

        if proxy is not None and server and not server.startswith("test://test:90"):
            context = await self.browser.new_context(proxy=proxy)
            try:
                async with browser_page(context) as page:
                    return await fn(self, page, *args, **kwargs)
            finally:
                await context.close()
        else:
            async with browser_page(self.context) as page:
                return await fn(self, page, *args, **kwargs)

    return wrapper
