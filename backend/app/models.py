from sqlalchemy import Integer, Float, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from .database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Device(Base):
    """Sensor cihazları - konum ve meta bilgiler"""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    
    # Konum bilgileri (harita için)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    city: Mapped[str] = mapped_column(String(128), index=True)
    district: Mapped[str] = mapped_column(String(128), index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utc_now)

    temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    hum_rh: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)

    tvoc_ppb: Mapped[float | None] = mapped_column(Float, nullable=True)
    eco2_ppm: Mapped[float | None] = mapped_column(Float, nullable=True)

    rssi: Mapped[float | None] = mapped_column(Float, nullable=True)
    snr: Mapped[float | None] = mapped_column(Float, nullable=True)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # OK/WARN/HIGH


Index("ix_device_ts", Measurement.device_id, Measurement.ts)