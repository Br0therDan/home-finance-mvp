from sqlmodel import Session, select

from core.models import AppSettings

# Minimal refactor to keep compatible signature


def get_base_currency(session: Session) -> str:
    statement = select(AppSettings).limit(1)
    settings = session.exec(statement).first()
    return settings.base_currency if settings else "KRW"


def set_base_currency(session: Session, currency: str) -> AppSettings:
    statement = select(AppSettings).limit(1)
    settings = session.exec(statement).first()
    if settings:
        settings.base_currency = currency
    else:
        settings = AppSettings(base_currency=currency)
        session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings
