import streamlit as st

from core.db import apply_migrations, get_connection


def main():
    st.set_page_config(
        page_title="Home Finance MVP",
        page_icon="💼",
        layout="wide",
    )

    # DB init
    conn = get_connection()
    apply_migrations(conn)

    st.title("Home Finance MVP")
    st.caption("Streamlit + SQLite 기반 가정용 자산/기장 관리 MVP")

    st.markdown(
        """
이 앱은 **가계부 입력 UX**를 제공하면서, 내부적으로는 **복식부기 원장(Journal)**을 저장하여
자동으로 **시산표 / 재무상태표(BS) / 손익(IS)**를 생성한다.

좌측 사이드바에서 페이지를 선택해 사용하면 된다.

- 거래 입력 → 자동 분개 생성
- 원장/시산표 조회
- 자산대장 + 평가이력 관리
- 리포트(BS/IS/Cashflow)
        """
    )

    st.info(
        "첫 실행 시 data/app.db 가 자동 생성되고 migrations/*.sql 이 순서대로 적용된다."
    )


if __name__ == "__main__":
    main()
