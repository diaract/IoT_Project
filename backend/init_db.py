"""
Initialize database and add sample devices
Usage: python init_db.py
"""

import sys
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Base, Device
from datetime import datetime, timezone

def init_database():
    """Create tables"""
    print("🔧 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")


def add_sample_devices():
    """Add sample devices"""
    db: Session = SessionLocal()
    
    try:
        # Check existing device count
        existing_count = db.query(Device).count()
        
        if existing_count > 0:
            print(f"⚠️  Database already contains {existing_count} devices.")
            response = input("Do you want to add new devices? (y/n): ")
            if response.lower() != 'y':
                print("❌ Cancelled.")
                return
        
        sample_devices = [
            Device(
                device_id="node-001",
                name="Kayseri Melikgazi - Ataturk Park",
                lat=38.7312,
                lon=35.4787,
                city="Kayseri",
                district="Melikgazi",
                created_at=datetime.now(timezone.utc)
            ),
            Device(
                device_id="node-002",
                name="Kayseri Kocasinan - Hospital Area",
                lat=38.7205,
                lon=35.4897,
                city="Kayseri",
                district="Kocasinan",
                created_at=datetime.now(timezone.utc)
            ),
            Device(
                device_id="node-003",
                name="Kayseri Talas - City Square",
                lat=38.6842,
                lon=35.5475,
                city="Kayseri",
                district="Talas",
                created_at=datetime.now(timezone.utc)
            ),
            Device(
                device_id="node-004",
                name="Istanbul Kadikoy - Moda Coast",
                lat=40.9875,
                lon=29.0290,
                city="Istanbul",
                district="Kadikoy",
                created_at=datetime.now(timezone.utc)
            ),
            Device(
                device_id="node-005",
                name="Istanbul Besiktas - Barbaros Square",
                lat=41.0429,
                lon=29.0082,
                city="Istanbul",
                district="Besiktas",
                created_at=datetime.now(timezone.utc)
            ),
            Device(
                device_id="node-006",
                name="Ankara Cankaya - Kizilay",
                lat=39.9208,
                lon=32.8541,
                city="Ankara",
                district="Cankaya",
                created_at=datetime.now(timezone.utc)
            ),
            Device(
                device_id="node-007",
                name="Izmir Karsiyaka - Coast",
                lat=38.4602,
                lon=27.1018,
                city="Izmir",
                district="Karsiyaka",
                created_at=datetime.now(timezone.utc)
            ),
        ]
        
        print(f"\n📝 Adding {len(sample_devices)} sample devices...")
        
        for device in sample_devices:
            # Check if device already exists
            existing = db.query(Device).filter(Device.device_id == device.device_id).first()
            
            if existing:
                print(f"⚠️  {device.device_id} already exists, skipping...")
                continue
            
            db.add(device)
            print(f"✅ {device.device_id}: {device.name} ({device.city}/{device.district})")
        
        db.commit()
        print(f"\n✅ Total {len(sample_devices)} devices successfully added!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def show_devices():
    """Show registered devices"""
    db: Session = SessionLocal()
    
    try:
        devices = db.query(Device).all()
        
        if not devices:
            print("\n❌ No devices in database!")
            return
        
        print(f"\n📋 Registered Devices ({len(devices)} total):")
        print("=" * 80)
        
        for device in devices:
            print(f"ID: {device.device_id}")
            print(f"   Name: {device.name}")
            print(f"   Location: {device.city}/{device.district}")
            print(f"   Coordinates: {device.lat}, {device.lon}")
            print(f"   Registered: {device.created_at}")
            print("-" * 80)
        
    finally:
        db.close()


def main():
    print("\n" + "=" * 80)
    print("Know The Air - Database Initialization")
    print("=" * 80 + "\n")
    
    # 1. Create tables
    init_database()
    
    # 2. Add sample devices
    add_sample_devices()
    
    # 3. Show devices
    show_devices()
    
    print("\n✅ Operation completed!")
    print("\n📌 Next Steps:")
    print("   1. Start backend: uvicorn main:app --reload")
    print("   2. Test API: http://localhost:8000/docs")
    print("   3. Check map: http://localhost:8000/map/points")
    print("   4. Connect ESP32 and start sending data\n")


if __name__ == "__main__":
    main()