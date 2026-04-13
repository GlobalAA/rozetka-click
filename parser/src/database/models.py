from datetime import datetime
from typing import override

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Proxy(Base):
    __tablename__: str = "proxies"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    server: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Shop(Base):
    __tablename__: str = "shops"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    url: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="shop",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @override
    def __repr__(self):
        return f"<Shop(id={self.id}, url={self.url})>"


class Category(Base):
    __tablename__: str = "categories"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    target_product: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    target_category: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    @override
    def __repr__(self):
        return f"<Category(id={self.id}, category={self.target_category})>"


class Product(Base):
    __tablename__: str = "products"

    id: Mapped[int] = mapped_column(
        Integer, Identity(), primary_key=True, autoincrement=True
    )

    product_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    shop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shops.id"), nullable=False
    )
    shop: Mapped["Shop"] = relationship("Shop", back_populates="products")

    @override
    def __repr__(self):
        return f"<Product(id={self.id})>"


class ParserStatus(Base):
    __tablename__: str = "parser_status"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    
    is_running: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

