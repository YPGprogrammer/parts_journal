"""Утилиты для работы с БД в Streamlit"""
from sqlalchemy.orm import Session
import streamlit as st
from .db import SessionLocal, init_db
from .services import ServiceContainer
from .models import Replacements


def get_db_session() -> Session:
    """Получить сессию БД из session_state или создать новую"""
    if 'db_session' not in st.session_state:
        st.session_state.db_session = SessionLocal()
    return st.session_state.db_session


def get_services() -> ServiceContainer:
    """Получить контейнер сервисов из session_state или создать новый"""
    if 'services' not in st.session_state:
        db = get_db_session()
        st.session_state.services = ServiceContainer(db)
    return st.session_state.services


def init_seed_data():
    """Инициализация начальных данных для справочников"""
    services = get_services()

    # Инициализация типов замен
    replacement_types = services.replacement_types.list()
    if not replacement_types:
        for replacement_type in Replacements:
            services.replacement_types.create(name=replacement_type)

    # Инициализация мастерских (опционально - можно добавить пример)
    # workshops = services.workshops.list()
    # if not workshops:
    #     services.workshops.create(name="Главная мастерская", addr="г. Москва, ул. Примерная, д. 1")


def init_app():
    """Инициализация приложения: создание БД и сервисов"""
    init_db()
    get_services()
    init_seed_data()
