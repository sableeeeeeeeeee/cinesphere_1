from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, utcnow


class SeatLock(Base):
    """Temporary hold. UNIQUE(show_id, seat_id) is what makes locking atomic."""
    __tablename__ = "seat_locks"
    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"), index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(64))  # per-browser-tab id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    __table_args__ = (UniqueConstraint("show_id", "seat_id", name="uq_lock_show_seat"),)


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"), index=True)
    status: Mapped[str] = mapped_column(String(15), default="confirmed")  # confirmed|cancelled
    payment_status: Mapped[str] = mapped_column(String(15), default="paid")  # paid|refunded|partially_refunded
    idempotency_key: Mapped[str] = mapped_column(String(64))
    # snapshot of money, all in paise
    tickets_total: Mapped[int] = mapped_column(Integer, default=0)
    food_total: Mapped[int] = mapped_column(Integer, default=0)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    fee: Mapped[int] = mapped_column(Integer, default=0)
    tax: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    coupon_code: Mapped[str | None] = mapped_column(String(40))
    refund_amount: Mapped[int] = mapped_column(Integer, default=0)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Snapshots so later edits to movie/cinema do not change old tickets
    movie_title: Mapped[str] = mapped_column(String(200), default="")
    cinema_name: Mapped[str] = mapped_column(String(160), default="")
    screen_name: Mapped[str] = mapped_column(String(80), default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    seats: Mapped[list["BookingSeat"]] = relationship(back_populates="booking", cascade="all, delete-orphan", lazy="selectin")
    show = relationship("Show", lazy="joined")
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_booking_idem"),)


class BookingSeat(Base):
    """Confirmed seat for a show. The partial unique index below is the final guard
    against double booking, no matter how many backend workers are running."""
    __tablename__ = "booking_seats"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))
    row_label: Mapped[str] = mapped_column(String(4))
    number_label: Mapped[str] = mapped_column(String(6))
    category: Mapped[str] = mapped_column(String(20))
    price: Mapped[int] = mapped_column(Integer)  # paise, price at booking time
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # False after cancellation
    booking: Mapped[Booking] = relationship(back_populates="seats")
    __table_args__ = (
        Index("uq_active_show_seat", "show_id", "seat_id", unique=True,
              postgresql_where=(is_active.is_(True)), sqlite_where=(is_active.is_(True))),
    )

    @property
    def label(self) -> str:
        return f"{self.row_label}{self.number_label}"


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(30), default="simulator")  # NOT a real gateway
    status: Mapped[str] = mapped_column(String(15))  # succeeded|failed
    amount: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
