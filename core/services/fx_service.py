from sqlmodel import Session


def get_latest_rate(session: Session, base_cur: str, target_cur: str) -> float:
    # TODO: Implement actual FX rates table
    if base_cur == target_cur:
        return 1.0
    return 1.0  # Mock
