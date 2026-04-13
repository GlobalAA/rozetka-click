from collections.abc import Sequence

from loguru import logger
from sqlalchemy import delete, select

from .models import Category, Product, Proxy, Shop, ParserStatus
from .session import async_session
from ..parser.exceptions import DuplicateObjectError


async def create_shop(url: str) -> int:
    async with async_session() as asession:
        scalar_found = await asession.scalar(
            select(Shop)
            .where(Shop.url == url)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not scalar_found:
            new_shop = Shop(url=url)
            asession.add(new_shop)

            await asession.commit()
            logger.info(f"Added new shop ({url})")
            return new_shop.id
        else:
            logger.error(f"Shop already exists: {url}")
            raise DuplicateObjectError(f"Shop with URL '{url}' already exists")


async def delete_products(shop_url: str) -> None:
    async with async_session() as asession:
        shop = await asession.scalar(
            select(Shop)
            .where(Shop.url == shop_url)
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        if shop:
            stmt = delete(Product).where(Product.shop_id == shop.id)

            await asession.execute(stmt)
            await asession.commit()


async def get_shops() -> Sequence[Shop]:
    async with async_session() as asession:
        shops = await asession.scalars(select(Shop))

        return shops.all()


async def get_categories() -> Sequence[Category]:
    async with async_session() as asession:
        categories = await asession.scalars(select(Category))

        return categories.all()


async def get_all_product_ids() -> set[str]:
    async with async_session() as asession:
        products = await asession.scalars(select(Product))
        return {p.product_id for p in products.all()}


async def create_category(target_product: str, target_category: str) -> int:
    async with async_session() as asession:
        scalar_found = await asession.scalar(
            select(Category)
            .where(Category.target_product == target_product, Category.target_category == target_category)
            .limit(1)
        )
        if not scalar_found:
            new_category = Category(
                target_product=target_product, target_category=target_category
            )
            asession.add(new_category)

            await asession.commit()
            logger.info(f"Added new category ({target_category})")
            return new_category.id
        else:
            logger.error(f"Category already exists: {target_category} ({target_product})")
            raise DuplicateObjectError(f"Category '{target_category}' for product '{target_product}' already exists")


async def create_product(product_id: str, shop_id: int) -> None:
    async with async_session() as asession:
        new_product = Product(product_id=product_id, shop_id=shop_id)

        asession.add(new_product)
        await asession.commit()


async def add_proxy(server: str, username: str, password: str) -> None:
    async with async_session() as asession:
        scalar_found = await asession.scalar(
            select(Proxy).where(Proxy.server == server).limit(1)
        )
        if scalar_found:
            logger.error(f"Proxy already exists: {server}")
            raise DuplicateObjectError(f"Proxy with server '{server}' already exists")

        new_proxy = Proxy(
            server=server,
            username=username,
            password=password,
        )

        asession.add(new_proxy)
        await asession.commit()
        logger.info(f"Added new proxy ({server})")


async def get_proxies() -> Sequence[Proxy]:
    async with async_session() as asession:
        proxies = await asession.scalars(select(Proxy))

        return proxies.all()


async def delete_shop(shop_id: int) -> bool:
    async with async_session() as asession:
        shop = await asession.scalar(select(Shop).where(Shop.id == shop_id).limit(1))
        if not shop:
            return False
        await asession.execute(delete(Product).where(Product.shop_id == shop_id))
        await asession.execute(delete(Shop).where(Shop.id == shop_id))
        await asession.commit()
        logger.info(f"Deleted shop (id={shop_id})")
        return True


async def delete_proxy(proxy_id: int) -> bool:
    async with async_session() as asession:
        result = await asession.execute(delete(Proxy).where(Proxy.id == proxy_id))
        await asession.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted proxy (id={proxy_id})")
        return deleted


async def delete_category(category_id: int) -> bool:
    async with async_session() as asession:
        result = await asession.execute(delete(Category).where(Category.id == category_id))
        await asession.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted category (id={category_id})")
        return deleted


async def get_parser_status() -> bool:
    async with async_session() as asession:
        status = await asession.scalar(select(ParserStatus).limit(1))
        if status:
            return status.is_running
        return False


async def set_parser_status(is_running: bool) -> None:
    async with async_session() as asession:
        status = await asession.scalar(select(ParserStatus).limit(1))
        if not status:
            status = ParserStatus(is_running=is_running)
            asession.add(status)
        else:
            status.is_running = is_running
        await asession.commit()
