-- 002_seed_accounts.sql
-- Minimal Chart of Accounts for household usage

INSERT OR IGNORE INTO accounts(name, type, parent_id, is_active) VALUES
  ('현금', 'ASSET', NULL, 1),
  ('보통예금', 'ASSET', NULL, 1),
  ('저축예금', 'ASSET', NULL, 1),
  ('증권계좌', 'ASSET', NULL, 1),
  ('전세보증금', 'ASSET', NULL, 1),
  ('부동산', 'ASSET', NULL, 1),

  ('카드미지급금', 'LIABILITY', NULL, 1),
  ('대출금', 'LIABILITY', NULL, 1),

  ('기초자본(Opening Balance)', 'EQUITY', NULL, 1),

  ('급여수익', 'INCOME', NULL, 1),
  ('기타수익', 'INCOME', NULL, 1),

  ('식비', 'EXPENSE', NULL, 1),
  ('교통비', 'EXPENSE', NULL, 1),
  ('주거/관리비', 'EXPENSE', NULL, 1),
  ('통신비', 'EXPENSE', NULL, 1),
  ('교육/육아', 'EXPENSE', NULL, 1),
  ('의료비', 'EXPENSE', NULL, 1),
  ('쇼핑', 'EXPENSE', NULL, 1),
  ('여가/취미', 'EXPENSE', NULL, 1),
  ('기타비용', 'EXPENSE', NULL, 1);
