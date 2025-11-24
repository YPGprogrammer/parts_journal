from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from enum import Enum
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String, Column, ForeignKey
from datetime import date


class Base(DeclarativeBase):
    pass

class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    available_units: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"Equipment(id={self.id!r}, name={self.name!r}, available units={self.available_units!r})"

class Workshop(Base):
    __tablename__ = "workshop"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    addr: Mapped[str] = mapped_column(String(100))

    def __repr__(self) -> str:
        return f"Workshop(id={self.id!r}, name={self.name!r}, address={self.addr!r})"

class Replacements(Enum):
    REPAIR = "repair"
    SCHEDULED = "scheduled replacement"
    UNSCHEDULED = "unscheduled replacement"

class ReplacementType(Base):
    __tablename__ = "replacement_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Replacements] = mapped_column(
    SQLEnum(Replacements, native_enum=False), 
    unique=True
)

class Part(Base):
    __tablename__ = "part"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    useful_life_days: Mapped[int] = mapped_column(Integer, default=100)
    parent_equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"))
    qty_per_unit: Mapped[int] = mapped_column(Integer)
    qty_in_stock: Mapped[int] = mapped_column(Integer)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=2)

class ReplacementLog(Base):
    __tablename__ = "replacement_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id"))
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"))
    unit_serial_number: Mapped[str] = mapped_column(String(30))
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshop.id"))
    replacement_type_id: Mapped[int] = mapped_column(ForeignKey("replacement_type.id"))
    installation_date: Mapped[date] = mapped_column(
        nullable=False
    )
    replacement_date: Mapped[date] = mapped_column(
        nullable=True
    )
    comments: Mapped[str] = mapped_column(String(200), nullable=True)