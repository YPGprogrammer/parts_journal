from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base

DB_URL = "sqlite:///./data/spares.db"

engine = create_engine(DB_URL, echo=False)

# фабрика обычных сессий
SessionLocal = sessionmaker(bind=engine)

# scoped_session — у каждого пользователя свой контекст
Session = scoped_session(SessionLocal)


def init_db():
    """Создаёт таблицы, если их нет."""
    Base.metadata.create_all(engine)


def get_session():
    """
    Возвращает сессию для текущего запроса Streamlit.
    Используется при инициализации сервисов.
    """
    return Session()
