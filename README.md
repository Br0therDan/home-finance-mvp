# Home Finance MVP (Streamlit + SQLite)

가정에서 사용하는 **재무/자산관리 툴 MVP**.

- **입력은 가계부 UX** (지출/수입/이체)
- **저장은 복식부기 원장(Journal)**
- 자동으로 **시산표 / 재무상태표(BS) / 손익계산서(IS) / 월별 현금흐름(Cashflow)** 생성
- **자산대장(유/무형) + 평가(valuation) 이력** 관리
- **정기 일정(구독) 관리 + 현금흐름 전망/자동 분개**

> 철학: “가계부처럼 쉽게 입력하고, 회계처럼 보고한다.”

---

## 1) 주요 기능

### 거래 입력 (가계부 UI)
- 지출(Expense)
- 수입(Income)
- 이체(Transfer)

입력 → 자동 분개 생성(대차평형 검증).

**자동 분개 규칙**
- 지출: (차) 비용계정 / (대) 결제계정(현금·예금·카드부채)
- 수입: (차) 입금계정(현금·예금) / (대) 수익계정
- 이체: (차) to(자산) / (대) from(자산)

카드 결제는 결제계정을 `카드미지급금`(LIABILITY)으로 선택하면 된다.

### 정기 일정(구독) 관리
- 월세/구독료 등 반복 거래를 등록
- 만기일 기준 현금흐름 전망 생성
- (옵션) 만기일에 자동 분개 생성

### 원장 / 시산표
- 전표 헤더(journal_entries) 목록
- 전표 라인(journal_lines) 목록
- Trial Balance(계정별 차/대 집계)

### 멀티 통화(Multi-currency) 지원
- **기준 통화(Base Currency)** 설정 (기본: KRW)
- **표시 통화(Display Currency)** 실시간 전환 (사이드바)
- 외화 계정(USD/JPY 등) 생성 및 거래 입력
- 거래 시점 환율(**Snapshot FX**) 자동 기록
- **장부 가액(Book Value)** vs **평가 가치(Current Value)** 비교 리포트
- 손익계산서(IS) 및 현금흐름(Cashflow)은 기준 통화 설정을 따름
- 수동 환율(Manual FX) 관리

### 계정 그룹(가계 친화 분류)
- 시스템(L1) 계정을 숨기고, 현금/은행/카드/투자/주거/차량/생활비/수입 등 **가정용 그룹**으로 묶어 표시

### Day0 기초 잔액 설정
- 과거 거래를 복원하지 않고 **오늘 기준 스냅샷**을 1회 입력
- `OPENING_BALANCE` 전표 1장만 생성
- 이후 모든 변화는 **Transactions(원장 분개)** 로만 누적

---

## 2) 스택

- UI: Streamlit
- DB: SQLite (WAL)
- DataFrame: pandas

---

## 3) 실행 방법

### 사전 준비
- Python 3.10+

### 설치 & 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py
```

최초 실행 시 자동으로:
- `data/app.db` 생성
- `migrations/*.sql` 적용
- 기본 계정과목(CoA) Seed 삽입

---

## 4) 프로젝트 구조

```
home-finance-mvp/
  app.py
  pages/
    0_Opening_Balance.py
    1_Dashboard.py
    2_Transactions.py
    3_Assets.py
    4_Ledger.py
    5_Reports.py
    6_Settings.py
    7_Subscriptions.py
  core/
    db.py
    models.py
    services/
      account_service.py
      ledger_service.py
      subscription_service.py
      asset_service.py
    ui/
      formatting.py
  alembic/
    versions/
  data/
    app.db (자동 생성)
  requirements.txt
```

---

## 4.1) UX 리디자인 참고 문서

- `REDESIGN_FOR_UX_ENHANCEMENT.md`: 가정용 자산 관리 중심 UX 목표와 데이터 모델 확장 계획을 정리한 문서

---

## 5) 데이터 모델(요약)

### accounts (계정과목)
- id
- name
- type: ASSET / LIABILITY / EQUITY / INCOME / EXPENSE
- parent_id (계층형 확장 용)
- is_active
- is_system (Level 1 시스템 계정 여부)
- level (계정 레벨: 시스템=1, 사용자=2+)
- allow_posting (직접 분개 허용 여부)

### journal_entries (전표 헤더)
- id
- entry_date
- description
- source

### journal_lines (전표 라인)
- entry_id
- account_id
- debit
- credit (장부 통화 기준)
- memo

### journal_line_fx (외화 스냅샷)
- line_id (journal_lines 연결)
- native_currency / native_amount
- fx_rate (거래 시점 환율)
- base_currency / base_amount

### fx_rates (환율 캐시)
- base_currency
- quote_currency
- rate
- as_of (기준일)

> **검증 규칙**
> - 한 전표의 debit 합 = credit 합 (대차평형, 장부 통화 기준)
> - 한 라인은 debit/credit 둘 중 하나만 허용

### assets (자산대장)
- name, asset_class
- linked_account_id (회계 반영용 연결 계정)
- acquisition_cost

### asset_valuations (평가 이력)
- asset_id, as_of_date
- value_native, currency
- method (market/appraisal/nav 등)
- fx_rate (기준 통화 환산용 스냅샷)

### 자산 평가 ↔ 원장 매핑 규칙
- 각 자산(`assets`)은 `linked_account_id`로 **단일 자산 계정**에 매핑된다.
- `asset_valuations`는 **정보용 스냅샷**이며, **자동 분개를 생성하지 않는다**.
- 대시보드에서 **평가 합계로 순자산을 계산**하고, **장부 자산 계정과의 대사 결과**를 표시한다.

### investment_profiles (투자 자산 프로필)
- asset_id (assets 연결, 1:1)
- ticker, exchange, trading_currency
- security_type, isin, broker

### investment_lots (보유 로트)
- asset_id, lot_date
- quantity, remaining_quantity
- unit_price_native, fees_native
- currency, fx_rate

### investment_events (투자 이벤트)
- asset_id, event_type(BUY/SELL/DIVIDEND), event_date
- quantity, price_per_unit_native, gross_amount_native
- fees_native, currency, fx_rate
- cash_account_id, income_account_id, fee_account_id
- journal_entry_id (자동 분개 연결용)

### subscriptions (정기 일정)
- name
- cadence / interval
- next_due_date
- amount
- debit_account_id / credit_account_id
- memo
- auto_create_journal
- last_run_date

---

## 6) 재무제표 계산 방식

### Raw Balance
각 계정의 raw balance:
- `SUM(debit - credit)`

### BS 표시(단순화)
- 자산(ASSET): raw balance가 대체로 +
- 부채/자본(LIABILITY/EQUITY): raw balance가 대체로 -

표시용으로:
- liabilities/equity는 `-raw_balance`로 양수화

`balanced_gap = assets - (liabilities + equity)`

> 가정용 MVP라서 표시 규칙은 단순화했다.
> (회계 실무의 정상잔액 표기까지 완벽히 재현하려면 계정별 normal-side를 강제해야 함)

### 월별 현금흐름 (Cashflow proxy)
- 현금성 계정(예: `현금`, `보통예금`, `정기예금`, 영문 cash/checking/savings 포함)을 기준으로 집계
- 월별 순변동(net change)과 기말 잔액(ending balance)을 표시

---

## 6.1) 투자 자산 평가 & 성과 지표

### 평가 방법(Valuation Methods)
- market: 시장가격 기반 평가
- nav: 펀드 순자산가치(NAV)
- appraisal: 수동 감정/평가

### 성과 지표(Performance Metrics)
- **Market Value**: 최신 valuation의 value_native
- **Cost Basis**: investment_lots 기준(수량 × 단가 + 수수료)
- **Unrealized P/L**: Market Value - Cost Basis

> 투자 자산 UX는 **자산 중심(asset-first)** 흐름을 유지한다.
> 사용자는 자산 화면에서 이벤트(매수/매도/배당)를 입력하고,
> 시스템이 ledger 자동 분개를 생성한다.

### 투자 이벤트 → 자동 분개 매핑(요약)
- BUY: (차) 투자자산 / (차) 수수료비용 / (대) 현금·결제계정
- SELL: (차) 현금·결제계정 / (대) 투자자산 / (대·차) 처분손익 / (차) 수수료비용
- DIVIDEND: (차) 현금·결제계정 / (대) 배당수익

---

## 7) 사용 팁

### L1/L2 계정 구조
- L1(시스템 계정)은 **집계 전용**이며 직접 분개 불가
- 실제 거래/오프닝밸런스는 L2(하위) 계정에만 기록
- 설정에서 L2 계정을 먼저 만든 뒤 거래 입력을 시작한다

### Day0 시작 방식
1) 좌측 사이드바에서 **Day0 기초 잔액 설정** 페이지로 이동
2) 자산/부채 잔액을 입력하고 **OPENING_BALANCE 전표**를 생성
3) 대시보드/리포트는 즉시 Day0 스냅샷 기준으로 집계됨

> 주의: OPENING_BALANCE 전표는 **1회만 생성** 가능 (재생성 기본 차단)

### 카드 결제
1) 거래 입력 → 지출
2) 결제 계정: `카드미지급금`

### 카드 대금 납부
- 이체(Transfer)로 “보통예금 → 카드미지급금”은 현재 UX에서 직접 지원하지 않는다.
- MVP 단계에서는 `원장` 페이지에서 수동 전표를 만들지 않으므로, 다음 라운드에서 **카드 납부 워크플로우**를 추가하는 게 좋다.

---

## 8) 다음 확장(추천)

- 카드 워크플로우: 카드사용/납부/할부
- 자산 처분/매각 손익 자동 분개
- 카테고리(가계부) ↔ 계정과목(CoA) 매핑 룰 엔진
- CSV Import/Export (은행/카드 사용내역)
- 멀티 통화 지원 (완료 - Phase 3/4)
- 자산 처분/매각 손익 자동 분개
- 카테고리(가계부) ↔ 계정과목(CoA) 매핑 룰 엔진
- CSV Import/Export (은행/카드 사용내역)

---

## License
개인 사용 목적 MVP 샘플.
