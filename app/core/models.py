from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from enum import Enum
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String, Column, ForeignKey, CheckConstraint, Index
from datetime import date


class Base(DeclarativeBase):
    pass

class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    available_units: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    parts: Mapped[list["Part"]] = relationship("Part", back_populates="parent_equipment", cascade="all, delete-orphan")
    replacement_logs: Mapped[list["ReplacementLog"]] = relationship("ReplacementLog", back_populates="equipment")

    __table_args__ = (
        CheckConstraint('available_units >= 0', name='check_available_units_positive'),
    )

    def __repr__(self) -> str:
        return f"Equipment(id={self.id!r}, name={self.name!r}, available units={self.available_units!r})"

class Workshop(Base):
    __tablename__ = "workshop"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    addr: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    replacement_logs: Mapped[list["ReplacementLog"]] = relationship("ReplacementLog", back_populates="workshop")

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
        unique=True,
        nullable=False
    )

    # Relationships
    replacement_logs: Mapped[list["ReplacementLog"]] = relationship("ReplacementLog", back_populates="replacement_type")

    def __repr__(self) -> str:
        return f"ReplacementType(id={self.id!r}, name={self.name.value!r})"

class Part(Base):
    __tablename__ = "part"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    useful_life_days: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    parent_equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    qty_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_in_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    # Relationships
    parent_equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="parts")
    replacement_logs: Mapped[list["ReplacementLog"]] = relationship("ReplacementLog", back_populates="part")

    __table_args__ = (
        CheckConstraint('useful_life_days > 0', name='check_useful_life_positive'),
        CheckConstraint('qty_per_unit > 0', name='check_qty_per_unit_positive'),
        CheckConstraint('qty_in_stock >= 0', name='check_qty_in_stock_non_negative'),
        CheckConstraint('lead_time_days >= 0', name='check_lead_time_non_negative'),
        Index('idx_part_equipment', 'parent_equipment_id'),
    )

    def __repr__(self) -> str:
        return f"Part(id={self.id!r}, name={self.name!r}, equipment_id={self.parent_equipment_id!r})"

class ReplacementLog(Base):
    __tablename__ = "replacement_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id"), nullable=False)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    unit_serial_number: Mapped[str] = mapped_column(String(30), nullable=False)
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshop.id"), nullable=False)
    replacement_type_id: Mapped[int] = mapped_column(ForeignKey("replacement_type.id"), nullable=False)
    installation_date: Mapped[date] = mapped_column(nullable=False)
    replacement_date: Mapped[date | None] = mapped_column(nullable=True)
    comments: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    part: Mapped["Part"] = relationship("Part", back_populates="replacement_logs")
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="replacement_logs")
    workshop: Mapped["Workshop"] = relationship("Workshop", back_populates="replacement_logs")
    replacement_type: Mapped["ReplacementType"] = relationship("ReplacementType", back_populates="replacement_logs")

    __table_args__ = (
        CheckConstraint(
            'replacement_date IS NULL OR replacement_date >= installation_date',
            name='check_replacement_date_after_installation'
        ),
        Index('idx_replacement_equipment', 'equipment_id'),
        Index('idx_replacement_part', 'part_id'),
        Index('idx_replacement_installation_date', 'installation_date'),
    )

    def __repr__(self) -> str:
        return f"ReplacementLog(id={self.id!r}, part_id={self.part_id!r}, equipment_id={self.equipment_id!r}, installation_date={self.installation_date!r})"
