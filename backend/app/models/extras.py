from datetime import datetime

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, utcnow


# ----------------------------------------------------------------- reviews
class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    user = relationship("User", lazy="joined")
    __table_args__ = (
        UniqueConstraint("movie_id", "user_id", name="uq_review_user_movie"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
    )


class ReviewVote(Base):
    __tablename__ = "review_votes"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    __table_args__ = (UniqueConstraint("review_id", "user_id", name="uq_vote"),)


class ReviewReport(Base):
    __tablename__ = "review_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(15), default="pending")  # pending|removed|dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    review = relationship("Review", lazy="joined")
    __table_args__ = (UniqueConstraint("review_id", "user_id", name="uq_report"),)


# -------------------------------------------------------------------- food
class FoodCategory(Base):
    __tablename__ = "food_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class FoodItem(Base):
    __tablename__ = "food_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("food_categories.id"))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(300), default="")
    image_url: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[int] = mapped_column(Integer)  # paise
    sizes: Mapped[list | None] = mapped_column(JSON)  # [{"name":"Large","extra":6000}]
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    stock: Mapped[int | None] = mapped_column(Integer)  # None = unlimited
    category = relationship("FoodCategory", lazy="joined")


class FoodOrder(Base):
    __tablename__ = "food_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(16), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    fulfilment: Mapped[str] = mapped_column(String(20), default="pickup")  # pickup | seat_delivery
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    tax: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    items: Mapped[list["FoodOrderItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


FOOD_STATUSES = ("pending", "confirmed", "preparing", "ready", "delivered", "cancelled")


class FoodOrderItem(Base):
    __tablename__ = "food_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("food_orders.id", ondelete="CASCADE"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("food_items.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160))  # snapshot
    size: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[int] = mapped_column(Integer)  # snapshot
    quantity: Mapped[int] = mapped_column(Integer)


# ----------------------------------------------------------------- coupons
class Coupon(Base):
    __tablename__ = "coupons"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(10))  # percent | fixed
    value: Mapped[int] = mapped_column(Integer)  # percent (0-100) or paise
    max_discount: Mapped[int | None] = mapped_column(Integer)
    min_order: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    cinema_id: Mapped[int | None] = mapped_column(ForeignKey("cinemas.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String(200), default="")


class CouponUsage(Base):
    __tablename__ = "coupon_usages"
    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    # one use per user per coupon
    __table_args__ = (UniqueConstraint("coupon_id", "user_id", name="uq_coupon_user"),)
