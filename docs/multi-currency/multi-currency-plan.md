# 목표
home-finance-mvp(Streamlit + SQLite) 프로젝트에 **멀티통화(특히 KRW + USD 중심)**를 도입하되, 다음 원칙을 동시에 만족시키는 “현실적인 가정용+투자용” 구조로 완성하라.

- **거래(원장) 집계는 “거래 시점 환율 스냅샷” 기반**으로 일관되게 유지 (auditability)
- **평가/대시보드 표시**는 “현재 환율/현재 시세” 기반으로도 별도로 제공 (real-world valuation)
- 해외주식 워크플로우(원화계좌 → 외화계좌 환전 → USD로 매매)가 자연스럽게 모델링되어야 한다.

---

# 핵심 원칙(Non-negotiable)
1) **SSOT는 journal_entries / journal_lines** 이다.
2) 원장 금액 집계/BS/IS 기본값은 **기준통화(Base Currency, 예: KRW)** 로 산출한다.
3) 외화 거래는 **원본통화(Native) + 환율 스냅샷 + 기준통화(Base) 환산값**을 함께 저장한다.
4) “현재환율/현재가치”는 **표시/평가 레이어**이며, 원장(SSOT)을 자동 수정하지 않는다.
5) 스키마 변경은 `migrations/`에 신규 파일로만 추가한다(기존 migration 수정 금지).
6) 멱등성(idempotent) 및 재현성(reproducible)이 중요하다: 거래 생성 후 같은 값을 다시 계산해도 동일해야 한다.

---

# 용어 정의(반드시 준수)
- **Base Currency**: 시스템 리포트/집계 기본 통화(예: KRW). Settings에서 지정.
- **Native Currency**: 특정 계정/거래의 원본 통화(예: USD).
- **Spot FX (Now)**: 현재 표시용 환율(대시보드 환산/평가용).
- **FX Snapshot**: 거래 시점에 확정한 환율(원장 환산 고정값). 반드시 저장.

---

# 기능 요구사항 (1) 통화 설정 & 표시 통화 스위치

## 1. Settings: Base Currency 설정
- Settings 페이지에 `base_currency` 설정을 추가한다.
- 기본값은 KRW.
- 저장 위치는 다음 중 하나:
  - `app_settings` 테이블(권장)
  - 또는 기존 settings 구조가 있으면 그에 맞게

## 2. Sidebar: Display Currency 선택
- 사이드바에 `display_currency` selectbox 제공
- 기본값은 base_currency
- 대시보드/리포트에서 “표시 값”을 바꿀 수 있어야 한다.
- 단, **원장/리포트의 기본 집계(장부가치)**는 base_currency 환산 스냅샷 기반으로 유지한다.

---

# 기능 요구사항 (2) 계정 단위 통화(Account Currency)

## accounts 테이블 확장 (migration)
- `currency` TEXT NOT NULL DEFAULT '<base_currency>' (예: 'KRW')
- 의미:
  - 계정은 “자기 통화”를 가진다.
  - 예: `보통예금 > 신한 원화계좌` = KRW
  - 예: `보통예금(외화) > 신한 USD 외화계좌` = USD
- 계정 생성 UI에서:
  - ASSET 계정의 경우 `currency` 선택을 허용(기본 base)
  - LIABILITY/EQUITY/INCOME/EXPENSE는 기본 base로 두되, 필요 시 허용 가능(우선 MVP에서는 ASSET만 허용해도 됨)

> L1/L2 정책이 적용된 상태라면, 통화는 실제 posting 가능한 L2 계정에만 의미가 크다.

---

# 기능 요구사항 (3) 원장에 FX 스냅샷 저장 (거래시점 환산 고정)

## 설계 방침(권장)
- `journal_lines`의 debit/credit는 **Base Currency 금액**을 유지한다(기존 리포트 안정성).
- 원본 통화 정보 및 환율 스냅샷은 별도 테이블로 저장한다(권장: 분리 테이블).

### 신규 테이블: `journal_line_fx` (migration)
필드:
- `id` INTEGER PK
- `line_id` INTEGER NOT NULL FK -> journal_lines.id UNIQUE
- `native_currency` TEXT NOT NULL
- `native_amount` REAL NOT NULL  (원본 금액, 부호 없이 “절대값” 권장)
- `base_currency` TEXT NOT NULL
- `fx_rate` REAL NOT NULL        (base per 1 native; 예: 1330 KRW per 1 USD)
- `base_amount` REAL NOT NULL    (native_amount * fx_rate, 검증용)
- `rate_source` TEXT NOT NULL DEFAULT 'manual'  (manual / api:xxx)
- `quoted_at` TEXT NULL          (timestamp)

## 저장 규칙
- 계정 통화가 base_currency와 같으면:
  - journal_line_fx는 생성하지 않아도 된다(선택)
- 계정 통화가 base_currency가 아니면(예: USD 계정):
  - 해당 라인에는 journal_line_fx를 반드시 생성한다.
  - `base_amount`는 해당 라인의 `debit` 또는 `credit`과 일치해야 한다(오차 허용 범위 적용).

## 검증
- ledger_service에서 journal entry 저장 시:
  - base 기준으로 대차평형(debit==credit) 체크
  - FX 라인 있는 경우 `abs(debit-credit) == base_amount` 등 정합성 체크

---

# 기능 요구사항 (4) 환율 데이터(현재환율 & 거래시점 환율)

## 1. FX Rates 테이블 (migration)
- `fx_rates`
  - `id` PK
  - `base_currency`
  - `quote_currency`
  - `rate`
  - `as_of` (timestamp or date)
  - `source`
  - UNIQUE(base_currency, quote_currency, as_of)

> 주의: rate 정의를 명확히 통일하라.  
> 본 프로젝트에서는 “base per 1 quote(=native)”로 통일한다.
> 예: base=KRW, quote=USD, rate=1330 (KRW per USD)

## 2. 환율 조회/캐시
- 외부 API 연동 전이라면:
  - 수동 입력으로 fx_rates 저장 가능(관리 UI)
- 외부 API 연동 후:
  - 최신 환율을 가져와 fx_rates에 저장(캐시)
- 거래 입력 시:
  - 기본값으로 최신 환율을 제안하고
  - 사용자가 override 가능
  - 최종적으로 FX Snapshot은 journal_line_fx에 고정 저장

---

# 기능 요구사항 (5) 거래 입력 UI: 멀티통화 대응

## Transactions 페이지 수정
### 공통 UX
- 사용자가 선택한 “결제/입금 계정”의 `currency`를 읽어,
  - base와 같으면 기존처럼
  - 다르면 (예: USD) 아래 입력이 추가로 뜨도록

### 외화 거래 입력 시 추가 입력
- `native_amount` (예: 12.99)
- `native_currency` (계정 통화로 자동)
- `fx_rate` (자동 제안 + 수동 override)
- 미리보기:
  - “장부 반영(KRW): 12.99 * 1330 = 17,267원”
  - “표시 통화(선택): …” (선택)

### 저장 로직
- journal_lines에는 base 금액으로 debit/credit 저장
- journal_line_fx에 원본 금액 + fx snapshot 저장

---

# 기능 요구사항 (6) 해외주식 워크플로우 템플릿 (중요)

다음 3가지 템플릿을 최소 지원하라.

## 1) 환전: KRW 계좌 → USD 계좌
입력:
- 출금 계정: KRW bank account (예: 신한KRW)
- 입금 계정: USD bank/broker cash account (예: 신한USD)
- USD amount (native) + fx_rate (snapshot)
- 선택: 수수료(비용) 분리

전표(개념):
- (차변) USD 계정 (base 금액)
- (대변) KRW 계정 (base 금액)
- (차변) 환전수수료 (선택)
- (대변) KRW 계정 (수수료)

FX:
- USD 계정 라인에 journal_line_fx 저장(native USD)
- KRW 계정 라인은 fx 없음

## 2) 해외unnable Trade: 해외주식 매수(USD)
MVP에서는 “포지션(수량/단가)”까지 완벽히 안 해도 되지만, 최소 2계정 구조로 처리:
- (차변) 투자자산(해외주식) (base)
- (대변) USD 캐시 계정 (base)
- FX: 두 라인 모두 USD-native 스냅샷 저장(둘 다 USD 계정이라면)

추가 옵션:
- 매수 수수료는 비용 계정으로 별도 라인 처리

## 3) 해외주식 매도(USD)
- (차변) USD 캐시 증가
- (대변) 투자자산 감소
- (대변/차변) 실현손익(수익/비용) (선택: MVP에서는 단순히 “투자손익” 계정 1개로 처리)

> 손익 계산을 정확히 하려면 평균단가/선입선출 등 포지션 로직이 필요하므로,
> MVP에서는 “매도 시 사용자가 손익을 입력”하거나,
> “단순 평균단가” 방식 중 하나를 선택 구현하라.

---

# 기능 요구사항 (7) “장부가치 vs 현재가치” 구분 표시 (대시보드/리포트)

## 1) 장부가치(Book Value)
- 원장 base 금액(거래시점 FX snapshot 기반)으로 계산한 값
- 대시보드 기본 총자산/총부채/순자산은 이것

## 2) 현재가치(Mark-to-Market / Display)
- 표시 통화 기준(사용자 선택)으로 “현재환율/현재시세”를 적용한 값
- 이는 별도의 섹션으로 보여준다:
  - 예: “현재가치(표시통화 기준)” / “장부가치(기준통화 기준)”를 나란히 표기
- 현재가치 산출 대상은 MVP에서 아래부터 시작:
  - 외화 현금/외화예금(USD 계정 잔액 * 현재환율)
  - (선택) 투자자산(주식) 평가: price_quotes * holdings (포지션 로직이 없으면 일단 제외)

> 중요한 방어선: 현재가치 표시는 원장 수정 없이 UI에서 계산한다.

---

# 기능 요구사항 (8) 외부 API(시장데이터 only) 연결 준비

## 1) API 어댑터 레이어
- `core/integrations/` 아래에 모듈 생성
  - `fx_provider.py`
  - `market_price_provider.py`
- 인터페이스는 단순히:
  - `get_latest_fx(base, quote) -> (rate, as_of, source)`
  - `get_latest_price(symbol) -> (price, currency, as_of, source)`
- 캐시는 fx_rates/price_quotes 테이블에 저장

## 2) 약관/안정성
- 실패 시에도 앱이 죽지 않도록:
  - API 실패 → 최근 캐시 사용
  - 캐시 없음 → 수동 입력 유도

---

# 마이그레이션 목록(예시)
- 007_add_account_currency.sql
- 008_add_journal_line_fx.sql
- 009_add_fx_rates.sql
- (선택) 010_add_price_quotes.sql
- (선택) 011_add_app_settings.sql

(번호는 현재 레포 상태에 맞게 조정)

---

# 완료 조건(Definition of Done)
1) base_currency 설정 가능 + sidebar display_currency 스위치 동작
2) 계정에 currency 지정 가능(최소 ASSET L2 계정)
3) 외화 계정 거래 입력 시 원본통화 + fx_rate 입력 및 저장(journal_line_fx)
4) 원장/리포트는 base 기준으로 안정적으로 집계됨(거래시점 FX snapshot 기반)
5) 대시보드에서 “장부가치(KRW)”와 “현재가치(표시통화)”를 구분 표시
6) 환전 템플릿(KRW→USD) 전표가 정상 생성되고 대차평형 유지
7) 앱이 `streamlit run app.py`로 정상 실행

---

# 로컬 실행 시나리오(검증 플로우)
1) base_currency=KRW 설정
2) 계정 생성:
   - 보통예금 > 신한KRW (currency=KRW)
   - 보통예금(외화) > 신한USD (currency=USD)  (필요 시 L1 추가)
3) 환율 입력:
   - KRW per USD = 1330 저장(fx_rates)
4) 환전 거래 입력:
   - 신한KRW에서 1,330,000 출금 → 신한USD로 1,000 USD 입금
   - journal_lines는 base로, journal_line_fx는 USD-native로 저장 확인
5) 대시보드:
   - 장부가치(기준통화)와 현재가치(표시통화) 구분 표기 확인
