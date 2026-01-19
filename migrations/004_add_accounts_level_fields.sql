-- 004_add_accounts_level_fields.sql
-- Add system/level/posting flags to accounts

ALTER TABLE accounts ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0;
ALTER TABLE accounts ADD COLUMN level INTEGER NOT NULL DEFAULT 2;
ALTER TABLE accounts ADD COLUMN allow_posting INTEGER NOT NULL DEFAULT 1;
