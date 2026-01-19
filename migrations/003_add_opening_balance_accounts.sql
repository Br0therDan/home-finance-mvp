-- 003_add_opening_balance_accounts.sql
-- Ensure required accounts for Day0 opening balance

INSERT OR IGNORE INTO accounts(name, type, parent_id, is_active) VALUES
  ('현금', 'ASSET', NULL, 1),
  ('보통예금', 'ASSET', NULL, 1),
  ('카드미지급금', 'LIABILITY', NULL, 1),
  ('대출금', 'LIABILITY', NULL, 1),
  ('기초순자산', 'EQUITY', NULL, 1);
