from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index,
                        Integer, String, Table, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, utcnow

SEAT_CATEGORIES = ("standard", "premium", "executive", "recliner", "balcony", "wheelchair", "companion")

movie_genres = Table(
    "movie_genres", Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    synopsis: Mapped[str] = mapped_column(Text, default="")
    poster_url: Mapped[str | None] = mapped_column(String(500))
    backdrop_url: Mapped[str | None] = mapped_column(String(500))
    trailer_url: Mapped[str | None] = mapped_column(String(500))  # YouTube embed URL
    director: Mapped[str | None] = mapped_column(String(120))
    cast: Mapped[list | None] = mapped_column(JSON, default=list)
    language: Mapped[str] = mapped_column(String(40), default="English", index=True)
    duration_min: Mapped[int] = mapped_column(Integer, default=120)
    certificate: Mapped[str] = mapped_column(String(10), default="UA")
    release_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(15), default="published", index=True)  # draft|published|archived
    avg_rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    genres: Mapped[list[Genre]] = relationship(secondary=movie_genres, lazy="selectin")


class Cinema(Base):
    __tablename__ = "cinemas"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(300), default="")
    phone: Mapped[str | None] = mapped_column(String(30))
    amenities: Mapped[list | None] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    screens: Mapped[list["Screen"]] = relationship(back_populates="cinema", cascade="all, delete-orphan")


class Screen(Base):
    __tablename__ = "screens"
    id: Mapped[int] = mapped_column(primary_key=True)
    cinema_id: Mapped[int] = mapped_column(ForeignKey("cinemas.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    label: Mapped[str | None] = mapped_column(String(80))  # e.g. "Audi 1 - Dolby Atmos"
    formats: Mapped[list] = mapped_column(JSON, default=lambda: ["2D"])
    # Structured layout, see services/layout.py for the shape:
    # {"row_labels": [...], "cols": N, "cells": [[null | {"n": "1", "c": "standard", "d": false}]]}
    layout: Mapped[dict | None] = mapped_column(JSON)
    layout_version: Mapped[int] = mapped_column(Integer, default=0)
    cinema: Mapped[Cinema] = relationship(back_populates="screens")


class Seat(Base):
    """Reusable physical seat. Stable id: never deleted once created, only deactivated."""
    __tablename__ = "seats"
    id: Mapped[int] = mapped_column(primary_key=True)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id", ondelete="CASCADE"), index=True)
    row_label: Mapped[str] = mapped_column(String(4))
    number_label: Mapped[str] = mapped_column(String(6))
    grid_row: Mapped[int] = mapped_column(Integer)
    grid_col: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20), default="standard")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # False = removed from layout
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)  # broken / blocked
    __table_args__ = (UniqueConstraint("screen_id", "row_label", "number_label", name="uq_seat_label"),)

    @property
    def label(self) -> str:
        return f"{self.row_label}{self.number_label}"


class Show(Base):
    __tablename__ = "shows"
    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # UTC
    ends_at: Mapped[datetime] = mapped_column(DateTime)  # UTC, includes cleaning buffer
    format: Mapped[str] = mapped_column(String(20), default="2D")
    language: Mapped[str] = mapped_column(String(40), default="English")
    status: Mapped[str] = mapped_column(String(15), default="scheduled")  # scheduled|cancelled
    prices: Mapped[dict] = mapped_column(JSON)  # {category: price_in_paise} -- snapshot copied to bookings
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    movie: Mapped[Movie] = relationship(lazy="joined")
    screen: Mapped[Screen] = relationship(lazy="joined")
    __table_args__ = (Index("ix_show_screen_time", "screen_id", "starts_at"),)
