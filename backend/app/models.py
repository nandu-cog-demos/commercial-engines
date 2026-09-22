import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class SbCategory(str, enum.Enum):
    OPTIONAL = "OPTIONAL"
    RECOMMENDED = "RECOMMENDED"
    MANDATORY = "MANDATORY"


class SbStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    TERMINATED = "TERMINATED"


class ComplianceStatus(str, enum.Enum):
    OPEN = "OPEN"
    COMPLIED = "COMPLIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AdBannerState(str, enum.Enum):
    RED = "RED"
    AMBER = "AMBER"
    GREEN = "GREEN"


class ShopVisitStatus(str, enum.Enum):
    INDUCTED = "INDUCTED"
    IN_WORK = "IN_WORK"
    RELEASED = "RELEASED"


class Engine(Base):
    __tablename__ = "engines"

    id: Mapped[int] = mapped_column(primary_key=True)
    serial: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    family: Mapped[str] = mapped_column(String(10), index=True)
    operator_code: Mapped[str] = mapped_column(String(10))
    operator_name: Mapped[str] = mapped_column(String(80))
    csn: Mapped[int] = mapped_column(Integer)  # cycles since new
    tsn: Mapped[int] = mapped_column(Integer)  # hours since new
    position: Mapped[str | None] = mapped_column(String(20))  # e.g. "N781NW / #2" or "SPARE"

    compliance: Mapped[list["SbCompliance"]] = relationship(back_populates="engine")
    shop_visits: Mapped[list["ShopVisit"]] = relationship(back_populates="engine")


class ServiceBulletin(Base):
    __tablename__ = "service_bulletins"

    id: Mapped[int] = mapped_column(primary_key=True)
    sb_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    family: Mapped[str] = mapped_column(String(10), index=True)
    category: Mapped[SbCategory] = mapped_column(Enum(SbCategory))
    status: Mapped[SbStatus] = mapped_column(Enum(SbStatus), default=SbStatus.ACTIVE)
    # Comma-separated inclusive serial-suffix ranges, e.g. "001000-001500,002200-002400".
    applicability_ranges: Mapped[str] = mapped_column(String(200))
    compliance_deadline_cycles: Mapped[int | None] = mapped_column(Integer)
    related_ad_number: Mapped[str | None] = mapped_column(String(30))
    issued_on: Mapped[date] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)

    compliance: Mapped[list["SbCompliance"]] = relationship(back_populates="service_bulletin")


class SbCompliance(Base):
    __tablename__ = "sb_compliance"
    __table_args__ = (UniqueConstraint("engine_id", "sb_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    engine_id: Mapped[int] = mapped_column(ForeignKey("engines.id"), index=True)
    sb_id: Mapped[int] = mapped_column(ForeignKey("service_bulletins.id"), index=True)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus), default=ComplianceStatus.OPEN
    )
    complied_date: Mapped[date | None] = mapped_column(Date)
    complied_at_csn: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    engine: Mapped[Engine] = relationship(back_populates="compliance")
    service_bulletin: Mapped[ServiceBulletin] = relationship(back_populates="compliance")


class ShopVisit(Base):
    __tablename__ = "shop_visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    engine_id: Mapped[int] = mapped_column(ForeignKey("engines.id"), index=True)
    shop: Mapped[str] = mapped_column(String(80))
    workscope: Mapped[str] = mapped_column(String(200))
    inducted_on: Mapped[date] = mapped_column(Date)
    status: Mapped[ShopVisitStatus] = mapped_column(
        Enum(ShopVisitStatus), default=ShopVisitStatus.INDUCTED
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime)
    released_by: Mapped[str | None] = mapped_column(String(80))

    engine: Mapped[Engine] = relationship(back_populates="shop_visits")
