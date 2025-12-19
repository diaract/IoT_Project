from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from .database import get_db
from .config import settings
from .schemas import (
    IngestPayload, IngestResponse, LatestResponse, MeasurementOut, 
    HistoryResponse, AlertLatestResponse, DeviceCreate, DeviceOut,
    MapPoint, MapPointsResponse, CitiesResponse, DistrictsResponse
)
from . import crud


router = APIRouter()

def require_api_key(x_api_key: str | None):
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.get("/health")
def health():
    return {"ok": True, "name": settings.APP_NAME}

@router.post("/ingest", response_model=IngestResponse)
def ingest(
    payload: IngestPayload,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
):
    require_api_key(x_api_key)
    m = crud.create_measurement(db, payload)
    return IngestResponse(ok=True, id=m.id)

@router.get("/latest", response_model=LatestResponse)
def latest(device_id: str = Query(...), db: Session = Depends(get_db)):
    m = crud.get_latest(db, device_id)
    if not m:
        return LatestResponse(found=False, data=None)

    out = MeasurementOut(
        device_id=m.device_id,
        ts=m.ts,
        temp_c=m.temp_c,
        hum_rh=m.hum_rh,
        pressure_hpa=m.pressure_hpa,
        tvoc_ppb=m.tvoc_ppb,
        eco2_ppm=m.eco2_ppm,
        rssi=m.rssi,
        snr=m.snr,
        score=m.score,   
        status=m.status     
    )

    return LatestResponse(found=True, data=out)


@router.get("/history", response_model=HistoryResponse)
def history(
    device_id: str = Query(...),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    items = crud.get_history(db, device_id, start, end, limit)
    out_items = [
        MeasurementOut(
        device_id=m.device_id, 
        ts=m.ts,
        temp_c=m.temp_c, 
        hum_rh=m.hum_rh, 
        pressure_hpa=m.pressure_hpa,
        tvoc_ppb=m.tvoc_ppb, 
        eco2_ppm=m.eco2_ppm,
        rssi=m.rssi, 
        snr=m.snr,
        score=m.score,
        status=m.status
        )
        for m in items
    ]
    return HistoryResponse(device_id=device_id, count=len(out_items), items=out_items)

@router.get("/alerts/latest", response_model=AlertLatestResponse)
def alerts_latest(device_id: str = Query(...), db: Session = Depends(get_db)):
    m = crud.get_latest(db, device_id)
    if not m:
        return AlertLatestResponse(found=False)

    return AlertLatestResponse(
        found=True,
        device_id=m.device_id,
        ts=m.ts,
        score=m.score,
        status=m.status,
        tvoc_ppb=m.tvoc_ppb,
        eco2_ppm=m.eco2_ppm,
    )


# Cihaz Yönetimi Endpoint'leri

@router.post("/devices/register", response_model=DeviceOut)
def register_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
):
    """Yeni cihaz kaydet"""
    require_api_key(x_api_key)
    
    # Cihaz zaten var mı kontrol et
    existing = crud.get_device(db, device.device_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Device already exists: {device.device_id}")
    
    db_device = crud.create_device(db, device)
    
    return DeviceOut(
        device_id=db_device.device_id,
        name=db_device.name,
        lat=db_device.lat,
        lon=db_device.lon,
        city=db_device.city,
        district=db_device.district,
        created_at=db_device.created_at
    )


@router.get("/devices/{device_id}", response_model=DeviceOut)
def get_device_info(device_id: str, db: Session = Depends(get_db)):
    """Cihaz bilgilerini getir"""
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    return DeviceOut(
        device_id=device.device_id,
        name=device.name,
        lat=device.lat,
        lon=device.lon,
        city=device.city,
        district=device.district,
        created_at=device.created_at
    )


# Harita Endpoint'leri

@router.get("/locations/cities", response_model=CitiesResponse)
def get_cities(db: Session = Depends(get_db)):
    """Tüm illeri listele"""
    cities = crud.get_all_cities(db)
    return CitiesResponse(cities=cities)


@router.get("/locations/districts", response_model=DistrictsResponse)
def get_districts(city: str = Query(..., description="İl adı"), db: Session = Depends(get_db)):
    """Seçilen ilin ilçelerini listele"""
    districts = crud.get_districts_by_city(db, city)
    
    if not districts:
        raise HTTPException(status_code=404, detail=f"No districts found for city: {city}")
    
    return DistrictsResponse(city=city, districts=districts)


@router.get("/map/points", response_model=MapPointsResponse)
def get_map_points(
    city: Optional[str] = Query(None, description="İl filtresi"),
    district: Optional[str] = Query(None, description="İlçe filtresi"),
    db: Session = Depends(get_db)
):
    """
    Harita için tüm sensor noktalarını getir
    Her cihaz için en son ölçümü ekle
    """
    # Cihazları filtrele
    if district and city:
        devices = crud.get_devices_by_district(db, city, district)
    elif city:
        devices = crud.get_devices_by_city(db, city)
    else:
        devices = crud.get_all_devices(db)
    
    points = []
    
    for device in devices:
        # En son ölçümü al
        latest = crud.get_latest(db, device.device_id)
        
        if latest:
            point = MapPoint(
                id=device.device_id,
                device_id=device.device_id,
                name=device.name,
                lat=device.lat,
                lon=device.lon,
                city=device.city,
                district=device.district,
                tvoc_ppb=latest.tvoc_ppb,
                eco2_ppm=latest.eco2_ppm,
                temperature=latest.temp_c,
                humidity=latest.hum_rh,
                pressure=latest.pressure_hpa,
                score=latest.score,
                status=latest.status,
                last_update=latest.ts
            )
        else:
            # Ölçüm yoksa sadece konum bilgisi
            point = MapPoint(
                id=device.device_id,
                device_id=device.device_id,
                name=device.name,
                lat=device.lat,
                lon=device.lon,
                city=device.city,
                district=device.district,
                tvoc_ppb=None,
                eco2_ppm=None,
                temperature=None,
                humidity=None,
                pressure=None,
                score=None,
                status="NO_DATA",
                last_update=None
            )
        
        points.append(point)
    
    return MapPointsResponse(points=points)