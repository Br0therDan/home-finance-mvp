-- migrations/012_restructure_account_ids.sql
-- Description: Restructure account IDs to a 4-digit hierarchical system.
-- All existing data is cleared to ensure consistency.

PRAGMA foreign_keys = OFF;

-- Clear all relevant tables
DELETE FROM journal_lines;
DELETE FROM journal_entries;
DELETE FROM asset_valuations;
DELETE FROM assets;
DELETE FROM accounts;

-- ASSET (1000-1999)
INSERT INTO accounts(id, name, type, parent_id, is_active, is_system, level, allow_posting) VALUES
(1000, '현금', 'ASSET', NULL, 1, 1, 1, 0),
(1100, '보통예금', 'ASSET', NULL, 1, 1, 1, 0),
(1200, '정기예금', 'ASSET', NULL, 1, 1, 1, 0),
(1300, '증권/투자자산', 'ASSET', NULL, 1, 1, 1, 0),
(1400, '부동산', 'ASSET', NULL, 1, 1, 1, 0),
(1500, '전세보증금(임차)', 'ASSET', NULL, 1, 1, 1, 0),
(1600, '대여금/미수금', 'ASSET', NULL, 1, 1, 1, 0),
(1700, '선급금/예치금', 'ASSET', NULL, 1, 1, 1, 0),
(1800, '차량/운송수단', 'ASSET', NULL, 1, 1, 1, 0),
(1900, '비품/장비', 'ASSET', NULL, 1, 1, 1, 0),
(1950, '기타자산', 'ASSET', NULL, 1, 1, 1, 0);

-- LIABILITY (2000-2999)
INSERT INTO accounts(id, name, type, parent_id, is_active, is_system, level, allow_posting) VALUES
(2000, '카드미지급금', 'LIABILITY', NULL, 1, 1, 1, 0),
(2100, '주택담보대출', 'LIABILITY', NULL, 1, 1, 1, 0),
(2200, '신용대출/기타대출', 'LIABILITY', NULL, 1, 1, 1, 0),
(2300, '전세보증금(임대)', 'LIABILITY', NULL, 1, 1, 1, 0),
(2400, '미지급금/외상', 'LIABILITY', NULL, 1, 1, 1, 0),
(2500, '세금/공과금 미지급', 'LIABILITY', NULL, 1, 1, 1, 0),
(2600, '기타부채', 'LIABILITY', NULL, 1, 1, 1, 0);

-- EQUITY (3000-3999)
INSERT INTO accounts(id, name, type, parent_id, is_active, is_system, level, allow_posting) VALUES
(3000, '자본/순자산', 'EQUITY', NULL, 1, 1, 1, 0),
(3001, '기초자본(Opening Balance)', 'EQUITY', 3000, 1, 0, 2, 1);

-- INCOME (4000-4999)
INSERT INTO accounts(id, name, type, parent_id, is_active, is_system, level, allow_posting) VALUES
(4000, '근로/급여수익', 'INCOME', NULL, 1, 1, 1, 0),
(4100, '사업/부업수익', 'INCOME', NULL, 1, 1, 1, 0),
(4200, '임대수익', 'INCOME', NULL, 1, 1, 1, 0),
(4300, '이자수익', 'INCOME', NULL, 1, 1, 1, 0),
(4400, '배당수익', 'INCOME', NULL, 1, 1, 1, 0),
(4500, '기타수익', 'INCOME', NULL, 1, 1, 1, 0);

-- EXPENSE (5000-5999)
INSERT INTO accounts(id, name, type, parent_id, is_active, is_system, level, allow_posting) VALUES
(5000, '식비', 'EXPENSE', NULL, 1, 1, 1, 0),
(5100, '주거/관리비', 'EXPENSE', NULL, 1, 1, 1, 0),
(5200, '공과금/통신', 'EXPENSE', NULL, 1, 1, 1, 0),
(5300, '교통/차량비', 'EXPENSE', NULL, 1, 1, 1, 0),
(5400, '교육/육아', 'EXPENSE', NULL, 1, 1, 1, 0),
(5500, '의료/건강', 'EXPENSE', NULL, 1, 1, 1, 0),
(5600, '보험료', 'EXPENSE', NULL, 1, 1, 1, 0),
(5700, '세금/수수료', 'EXPENSE', NULL, 1, 1, 1, 0),
(5800, '이자비용', 'EXPENSE', NULL, 1, 1, 1, 0),
(5900, '소비/쇼핑', 'EXPENSE', NULL, 1, 1, 1, 0),
(5910, '여행/여가', 'EXPENSE', NULL, 1, 1, 1, 0),
(5920, '감가상각비', 'EXPENSE', NULL, 1, 1, 1, 0),
(5930, '기타비용', 'EXPENSE', NULL, 1, 1, 1, 0);

PRAGMA foreign_keys = ON;
