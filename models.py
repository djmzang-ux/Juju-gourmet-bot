from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    orders = relationship("Order", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10,2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(80), default="Trufas")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    fulfillment: Mapped[str] = mapped_column(String(20), default="delivery")
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(40))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    payment_status: Mapped[str] = mapped_column(String(30), default="pending")
    payment_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10,2))
    order = relationship("Order", back_populates="items")

class Coupon(Base):
    __tablename__ = "coupons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    percent: Mapped[Decimal] = mapped_column(Numeric(5,2), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
