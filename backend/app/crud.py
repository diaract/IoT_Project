from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from datetime import datetime, timezone
from .models import Measurement, Device
from .schemas import IngestPayload, DeviceCreate
from .alerts import evaluate_alert


def create_measurement(db: Session, payload: IngestPayload) -> Measurement:
    ts = payload.ts or datetime.now(timezone.utc)
    m = Measurement(
        device_id=payload.device_id,
        ts=ts,
        temp_c=payload.temp_c,
        hum_rh=payload.hum_rh,
        pressure_hpa=payload.pressure_hpa,
        tvoc_ppb=payload.tvoc_ppb,
        eco2_ppm=payload.eco2_ppm,
        rssi=payload.rssi,
        snr=payload.snr,
        
    )
    alert = evaluate_alert(db, payload.device_id, ts, payload.tvoc_ppb, payload.eco2_ppm)
    m.score = alert.score
    m.status = alert.status

    db.add(m)
    db.commit()
    db.refresh(m)
    return m

def get_latest(db: Session, device_id: str) -> Measurement | None:
    stmt = select(Measurement).where(Measurement.device_id == device_id).order_by(desc(Measurement.ts)).limit(1)
    return db.execute(stmt).scalars().first()

def get_history(db: Session, device_id: str, start, end, limit: int) -> list[Measurement]:
    stmt = select(Measurement).where(Measurement.device_id == device_id)
    if start:
        stmt = stmt.where(Measurement.ts >= start)
    if end:
        stmt = stmt.where(Measurement.ts <= end)
    stmt = stmt.order_by(Measurement.ts.asc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


# Device CRUD fonksiyonları

def create_device(db: Session, device: DeviceCreate) -> Device:
    """Yeni cihaz oluştur"""
    db_device = Device(
        device_id=device.device_id,
        name=device.name,
        lat=device.lat,
        lon=device.lon,
        city=device.city,
        district=device.district
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def get_device(db: Session, device_id: str) -> Device | None:
    """Cihaz bilgilerini getir"""
    stmt = select(Device).where(Device.device_id == device_id)
    return db.execute(stmt).scalars().first()


def get_all_devices(db: Session) -> list[Device]:
    """Tüm cihazları getir"""
    stmt = select(Device)
    return list(db.execute(stmt).scalars().all())


def get_devices_by_city(db: Session, city: str) -> list[Device]:
    """Belirli bir ildeki cihazları getir"""
    stmt = select(Device).where(Device.city == city)
    return list(db.execute(stmt).scalars().all())


def get_devices_by_district(db: Session, city: str, district: str) -> list[Device]:
    """Belirli bir ilçedeki cihazları getir"""
    stmt = select(Device).where(Device.city == city).where(Device.district == district)
    return list(db.execute(stmt).scalars().all())


def get_all_cities(db: Session) -> list[str]:
    """Tüm illeri getir"""
    stmt = select(Device.city).distinct()
    cities = db.execute(stmt).scalars().all()
    return sorted([c for c in cities if c])


def get_districts_by_city(db: Session, city: str) -> list[str]:
    """Belirli bir ilin ilçelerini getir"""
    stmt = select(Device.district).where(Device.city == city).distinct()
    districts = db.execute(stmt).scalars().all()
    return sorted([d for d in districts if d])