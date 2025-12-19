from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class IngestPayload(BaseModel):
    device_id: str = Field(..., examples=["node-001"])
    ts: Optional[datetime] = Field(None, description="ISO timestamp; boşsa server UTC now kullanır")

    temp_c: Optional[float] = None
    hum_rh: Optional[float] = None
    pressure_hpa: Optional[float] = None

    tvoc_ppb: Optional[float] = None
    eco2_ppm: Optional[float] = None

    rssi: Optional[float] = None
    snr: Optional[float] = None

class IngestResponse(BaseModel):
    ok: bool
    id: int

class MeasurementOut(BaseModel):
    device_id: str
    ts: datetime
    temp_c: Optional[float] = None
    hum_rh: Optional[float] = None
    pressure_hpa: Optional[float] = None
    tvoc_ppb: Optional[float] = None
    eco2_ppm: Optional[float] = None
    rssi: Optional[float] = None
    snr: Optional[float] = None
    score: Optional[float] = None
    status: Optional[str] = None


class LatestResponse(BaseModel):
    found: bool
    data: Optional[MeasurementOut] = None

class HistoryResponse(BaseModel):
    device_id: str
    count: int
    items: List[MeasurementOut]

class AlertLatestResponse(BaseModel):
    found: bool
    device_id: Optional[str] = None
    ts: Optional[datetime] = None
    score: Optional[float] = None
    status: Optional[str] = None
    tvoc_ppb: Optional[float] = None
    eco2_ppm: Optional[float] = None


#  Harita için schema'lar
class DeviceCreate(BaseModel):
    """Yeni cihaz oluşturma"""
    device_id: str
    name: str
    lat: float
    lon: float
    city: str
    district: str


class DeviceOut(BaseModel):
    """Cihaz bilgileri"""
    device_id: str
    name: str
    lat: float
    lon: float
    city: str
    district: str
    created_at: datetime


class MapPoint(BaseModel):
    """Harita üzerinde bir nokta"""
    id: str
    device_id: str
    name: str
    lat: float
    lon: float
    city: str
    district: str
    tvoc_ppb: Optional[float] = None
    eco2_ppm: Optional[float] = None
    temperature: Optional[float] = None  # temp_c olarak gelir
    humidity: Optional[float] = None     # hum_rh olarak gelir
    pressure: Optional[float] = None     # pressure_hpa olarak gelir
    score: Optional[float] = None
    status: Optional[str] = None
    last_update: Optional[datetime] = None


class MapPointsResponse(BaseModel):
    """Harita noktaları yanıtı"""
    points: List[MapPoint]


class CitiesResponse(BaseModel):
    """İl listesi yanıtı"""
    cities: List[str]


class DistrictsResponse(BaseModel):
    """İlçe listesi yanıtı"""
    city: str
    districts: List[str]