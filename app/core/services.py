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

def compute_wear(part_useful_life_days: int, installation_date: date, replacement_date: date | None = None,
                 qty_in_stock: int = 0, lead_time_days: int = 0):
    """
    Возвращает:
    - процент остатка (0..1)
    - число оставшихся дней
    - цвет зоны: green/yellow/red

    Если запчасти нет на складе (qty_in_stock == 0), учитывает срок доставки.
    """
    today = date.today()
    end_date = replacement_date or today

    used_days = (end_date - installation_date).days
    remaining_days = part_useful_life_days - used_days

    # Если запчасти нет на складе, вычитаем срок доставки из оставшихся дней
    if qty_in_stock == 0 and lead_time_days > 0:
        remaining_days = remaining_days - lead_time_days

    percentage_left = remaining_days / part_useful_life_days if part_useful_life_days > 0 else 0

    if percentage_left > 0.25:
        zone = "green"
    elif percentage_left > 0.10:
        zone = "yellow"
    else:
        zone = "red"

    return percentage_left, remaining_days, zone


PURCHASE_DAYS = (10, 25)


def nearest_purchase_day(target_date: date) -> date:
    """
    Возвращает ближайшую дату закупки: 10 или 25 число.
    Если день 1-9: возвращает 10 число текущего месяца
    Если день 10-24: возвращает 25 число текущего месяца (или 10, если уже прошло 25)
    Если день 25-31: возвращает 10 число следующего месяца
    """
    day = target_date.day

    if day <= 9:
        # До 9 числа - можно закупить 10 числа текущего месяца
        return target_date.replace(day=10)
    elif day <= 24:
        # До 24 числа - можно закупить 25 числа текущего месяца
        return target_date.replace(day=25)
    else:
        # После 24 числа - следующая закупка 10 числа следующего месяца
        if target_date.month == 12:
            return date(target_date.year + 1, 1, 10)
        return date(target_date.year, target_date.month + 1, 10)


def previous_purchase_day(target_date: date) -> date:
    """
    Возвращает предыдущую дату закупки (10 или 25 число) до указанной даты.
    Используется для расчета самой поздней даты инициации закупки.
    """
    day = target_date.day

    if day >= 25:
        # Если 25 или позже - можно было закупить 25 числа текущего месяца
        return target_date.replace(day=25)
    elif day >= 10:
        # Если 10-24 - можно было закупить 10 числа текущего месяца
        return target_date.replace(day=10)
    else:
        # Если до 10 - нужно было закупить 25 числа предыдущего месяца
        if target_date.month == 1:
            return date(target_date.year - 1, 12, 25)
        # Проверяем, сколько дней в предыдущем месяце
        from calendar import monthrange
        prev_month = target_date.month - 1
        prev_year = target_date.year
        _, last_day = monthrange(prev_year, prev_month)
        return date(prev_year, prev_month, min(25, last_day))


def compute_latest_init_date(installation_date: date, useful_life_days: int, lead_time_days: int):
    """
    Высчитывает последнюю дату, когда можно инициировать закупку.

    По ТЗ: "Запчасти могут быть закуплены 10-го и 25-го числа, следующего за датой
    инициации закупки + срок закупки запчасти."

    Интерпретация: если инициируем закупку в месяце M, то закупка произойдет
    10 или 25 числа месяца M+1, а получение через lead_time_days после закупки.

    Логика:
    1. failure_date = дата окончания срока службы запчасти
    2. Нужно получить запчасть до failure_date
    3. Перебираем возможные даты закупки (10 и 25 числа) и находим самую позднюю,
       такую что закупка + lead_time_days <= failure_date
    4. От даты закупки вычисляем дату инициации (месяц до закупки)
    """
    failure_date = installation_date + timedelta(days=useful_life_days)

    # Перебираем возможные даты закупки (10 и 25 числа) в обратном порядке
    # и находим самую позднюю, такую что закупка + lead_time_days <= failure_date
    candidates = []

    # Проверяем даты закупки в текущем и предыдущих месяцах
    for months_back in range(0, 13):  # Проверяем до года назад
        if months_back == 0:
            check_year = failure_date.year
            check_month = failure_date.month
        else:
            if failure_date.month > months_back:
                check_year = failure_date.year
                check_month = failure_date.month - months_back
            else:
                check_year = failure_date.year - 1
                check_month = 12 - (months_back - failure_date.month)

        # Проверяем 25 число
        try:
            purchase_25 = date(check_year, check_month, 25)
            receipt_25 = purchase_25 + timedelta(days=lead_time_days)
            if receipt_25 <= failure_date:
                # Инициация должна быть в предыдущем месяце
                if check_month == 1:
                    init_date = date(check_year - 1, 12, 1)
                else:
                    init_date = date(check_year, check_month - 1, 1)
                candidates.append((purchase_25, init_date, receipt_25))
        except ValueError:
            pass

        # Проверяем 10 число
        try:
            purchase_10 = date(check_year, check_month, 10)
            receipt_10 = purchase_10 + timedelta(days=lead_time_days)
            if receipt_10 <= failure_date:
                # Инициация должна быть в предыдущем месяце
                if check_month == 1:
                    init_date = date(check_year - 1, 12, 1)
                else:
                    init_date = date(check_year, check_month - 1, 1)
                candidates.append((purchase_10, init_date, receipt_10))
        except ValueError:
            pass

    # Находим самую позднюю дату закупки
    if candidates:
        latest_purchase_date, latest_init_date, receipt_date = max(candidates, key=lambda x: x[0])
    else:
        # Если ничего не найдено (маловероятно), используем безопасные значения
        latest_purchase_date = failure_date - timedelta(days=lead_time_days + 30)
        latest_init_date = latest_purchase_date - timedelta(days=30)
        receipt_date = latest_purchase_date + timedelta(days=lead_time_days)

    return {
        "failure_date": failure_date,
        "latest_init_date": latest_init_date,
        "latest_purchase_date": latest_purchase_date,
        "receipt_date": receipt_date,
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

    def update(self, equipment_id: int, **kwargs):
        obj = self.get(equipment_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        self.db.commit()
        return obj

    def delete(self, equipment_id: int):
        obj = self.get(equipment_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj


class WorkshopService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(Workshop).all()

    def get(self, workshop_id: int):
        return self.db.query(Workshop).filter(Workshop.id == workshop_id).first()

    def create(self, **kwargs):
        obj = Workshop(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, workshop_id: int, **kwargs):
        obj = self.get(workshop_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        self.db.commit()
        return obj

    def delete(self, workshop_id: int):
        obj = self.get(workshop_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj


class ReplacementTypeService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(ReplacementType).all()

    def get(self, type_id: int):
        return self.db.query(ReplacementType).filter(ReplacementType.id == type_id).first()

    def create(self, **kwargs):
        obj = ReplacementType(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, type_id: int, **kwargs):
        obj = self.get(type_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        self.db.commit()
        return obj

    def delete(self, type_id: int):
        obj = self.get(type_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj


class ReplacementService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(ReplacementLog).all()

    def get(self, replacement_id: int):
        return self.db.query(ReplacementLog).filter(ReplacementLog.id == replacement_id).first()

    def create(self, **kwargs):
        obj = ReplacementLog(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, replacement_id: int, **kwargs):
        obj = self.get(replacement_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        self.db.commit()
        return obj

    def delete(self, replacement_id: int):
        obj = self.get(replacement_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj

    def get_by_equipment(self, equipment_id: int):
        return (
            self.db.query(ReplacementLog)
            .filter(ReplacementLog.equipment_id == equipment_id)
            .order_by(ReplacementLog.installation_date.desc())
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
