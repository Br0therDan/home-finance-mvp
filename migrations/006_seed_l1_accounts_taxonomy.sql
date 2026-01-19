-- 006_seed_l1_accounts_taxonomy.sql
-- Seed L1 system accounts from l1-accounts-taxonomy.md

INSERT OR IGNORE INTO accounts(name, type, parent_id, is_active, is_system, level, allow_posting) VALUES
  -- ASSET
  ('현금', 'ASSET', NULL, 1, 1, 1, 0),
  ('보통예금', 'ASSET', NULL, 1, 1, 1, 0),
  ('정기예금', 'ASSET', NULL, 1, 1, 1, 0),
  ('증권/투자자산', 'ASSET', NULL, 1, 1, 1, 0),
  ('부동산', 'ASSET', NULL, 1, 1, 1, 0),
  ('전세보증금(임차)', 'ASSET', NULL, 1, 1, 1, 0),
  ('대여금/미수금', 'ASSET', NULL, 1, 1, 1, 0),
  ('선급금/예치금', 'ASSET', NULL, 1, 1, 1, 0),
  ('차량/운송수단', 'ASSET', NULL, 1, 1, 1, 0),
  ('비품/장비', 'ASSET', NULL, 1, 1, 1, 0),
  ('기타자산', 'ASSET', NULL, 1, 1, 1, 0),

  -- LIABILITY
  ('카드미지급금', 'LIABILITY', NULL, 1, 1, 1, 0),
  ('주택담보대출', 'LIABILITY', NULL, 1, 1, 1, 0),
  ('신용대출/기타대출', 'LIABILITY', NULL, 1, 1, 1, 0),
  ('전세보증금(임대)', 'LIABILITY', NULL, 1, 1, 1, 0),
  ('미지급금/외상', 'LIABILITY', NULL, 1, 1, 1, 0),
  ('세금/공과금 미지급', 'LIABILITY', NULL, 1, 1, 1, 0),
  ('기타부채', 'LIABILITY', NULL, 1, 1, 1, 0),

  -- EQUITY
  ('자본/순자산', 'EQUITY', NULL, 1, 1, 1, 0),

  -- INCOME
  ('근로/급여수익', 'INCOME', NULL, 1, 1, 1, 0),
  ('사업/부업수익', 'INCOME', NULL, 1, 1, 1, 0),
  ('임대수익', 'INCOME', NULL, 1, 1, 1, 0),
  ('이자수익', 'INCOME', NULL, 1, 1, 1, 0),
  ('배당수익', 'INCOME', NULL, 1, 1, 1, 0),
  ('기타수익', 'INCOME', NULL, 1, 1, 1, 0),

  -- EXPENSE
  ('식비', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('주거/관리비', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('공과금/통신', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('교통/차량비', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('교육/육아', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('의료/건강', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('보험료', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('세금/수수료', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('이자비용', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('소비/쇼핑', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('여행/여가', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('감가상각비', 'EXPENSE', NULL, 1, 1, 1, 0),
  ('기타비용', 'EXPENSE', NULL, 1, 1, 1, 0);

-- Link opening equity leaf to L1 equity parent if present
UPDATE accounts
SET parent_id = (SELECT id FROM accounts WHERE name='자본/순자산' AND type='EQUITY')
WHERE name IN ('기초순자산', '기초자본(Opening Balance)')
  AND type='EQUITY'
  AND parent_id IS NULL;
