from sqlmodel import Session

# Minimal refactor to keep compatible signature


def get_base_currency(session: Session) -> str:
    # TODO: Implement actual settings model/table
    return "KRW"
