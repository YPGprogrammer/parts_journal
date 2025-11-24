from datetime import date, timedelta
from sqlalchemy.orm import Session

from .models import (
    Part,
    Equipment,
    Workshop,
    ReplacementType,
    ReplacementLog
)

# -------------------------------
#  Вспомогательные функции
# -------------------------------

def compute_wear(part_useful_life_days: int, installation_date: date, replacement_date: date | None = None):
    """
    Возвращает:
    - процент остатка (0..1)
    - число оставшихся дней
    - цвет зоны: green/yellow/red
    """
    today = date.today()
    end_date = replacement_date or today

    used_days = (end_date - installation_date).days
    remaining_days = part_useful_life_days - used_days

    percentage_left = remaining_days / part_useful_life_days

    if percentage_left > 0.25:
        zone = "green"
    elif percentage_left > 0.10:
        zone = "yellow"
    else:
        zone = "red"

    return percentage_left, remaining_days, zone


PURCHASE_DAYS = (10, 25)


def nearest_purchase_day(target_date: date) -> date:
    """Возвращает ближайшую дату закупки: 10 или 25 число."""
    day = target_date.day

    for d in PURCHASE_DAYS:
        if day <= d:
            return target_date.replace(day=d)

    # Следующий месяц
    if target_date.month == 12:
        return date(target_date.year + 1, 1, 10)

    return date(target_date.year, target_date.month + 1, 10)


def compute_latest_init_date(installation_date: date, useful_life_days: int, lead_time_days: int):
    """Высчитывает последнюю дату, когда можно инициировать закупку."""
    failure_date = installation_date + timedelta(days=useful_life_days)
    raw_latest = failure_date - timedelta(days=lead_time_days)
    final_latest = nearest_purchase_day(raw_latest)

    return {
        "failure_date": failure_date,
        "raw_latest": raw_latest,
        "latest_purchase": final_latest,
    }


# -------------------------------
#  Сервисный слой
# -------------------------------

class PartService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(Part).all()

    def get(self, part_id: int):
        return self.db.query(Part).filter(Part.id == part_id).first()

    def create(self, **kwargs):
        obj = Part(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, part_id: int, **kwargs):
        obj = self.get(part_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        self.db.commit()
        return obj

    def delete(self, part_id: int):
        obj = self.get(part_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj


class EquipmentService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(Equipment).all()

    def get(self, id: int):
        return self.db.query(Equipment).filter(Equipment.id == id).first()

    def create(self, **kwargs):
        obj = Equipment(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj


class WorkshopService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(Workshop).all()


class ReplacementTypeService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(ReplacementType).all()


class ReplacementService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(ReplacementLog).all()

    def create(self, **kwargs):
        obj = ReplacementLog(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_by_equipment(self, equipment_id: int):
        return (
            self.db.query(ReplacementLog)
            .filter(ReplacementLog.equipment_id == equipment_id)
            .order_by(ReplacementLog.replacement_date.desc())
            .all()
        )


class ProcurementPlanService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_for_part(self, part: Part, installation_date: date):
        """Расчёт плана закупки по одной запчасти."""
        return compute_latest_init_date(
            installation_date=installation_date,
            useful_life_days=part.useful_life_days,
            lead_time_days=part.lead_time_days,
        )


# -------------------------------
#  Фабрика сервисов
# -------------------------------

class ServiceContainer:
    """Удобный контейнер для Streamlit: st.session_state['services']"""

    def __init__(self, db: Session):
        self.parts = PartService(db)
        self.equipment = EquipmentService(db)
        self.workshops = WorkshopService(db)
        self.replacement_types = ReplacementTypeService(db)
        self.replacements = ReplacementService(db)
        self.procurement = ProcurementPlanService(db)
