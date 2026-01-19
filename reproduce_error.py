from sqlmodel import Session, select
from core.db import engine
from core.models import Account, JournalEntry, JournalLine


def reproduce():
    try:
        session = Session(engine)
        # 1. Initialize mappers
        statement = select(Account)
        session.exec(statement).all()
        print("Mappers initialized successfully.")

        # 2. Trigger Relationship configuration
        entry_statement = select(JournalEntry)
        session.exec(entry_statement).first()
        print("JournalEntry relationships configured successfully.")

        line_statement = select(JournalLine)
        session.exec(line_statement).first()
        print("JournalLine relationships configured successfully.")

    except Exception as e:
        print(f"Caught error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce()
