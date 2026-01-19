-- 005_promote_seed_accounts_to_system.sql
-- Promote known L1 seed accounts to system (level=1, allow_posting=0)

UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='현금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='보통예금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='정기예금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='증권/투자자산' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='부동산' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='전세보증금(임차)' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='전세보증금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='저축예금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='대여금/미수금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='선급금/예치금' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='차량/운송수단' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='비품/장비' AND type='ASSET';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='기타자산' AND type='ASSET';

UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='카드미지급금' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='주택담보대출' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='신용대출/기타대출' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='대출금' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='전세보증금(임대)' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='미지급금/외상' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='세금/공과금 미지급' AND type='LIABILITY';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='기타부채' AND type='LIABILITY';

UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='자본/순자산' AND type='EQUITY';

UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='근로/급여수익' AND type='INCOME';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='사업/부업수익' AND type='INCOME';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='임대수익' AND type='INCOME';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='이자수익' AND type='INCOME';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='배당수익' AND type='INCOME';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='기타수익' AND type='INCOME';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='급여수익' AND type='INCOME';

UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='식비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='주거/관리비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='공과금/통신' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='교통/차량비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='교육/육아' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='의료/건강' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='보험료' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='세금/수수료' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='이자비용' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='소비/쇼핑' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='여행/여가' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='감가상각비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='기타비용' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='교통비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='통신비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='의료비' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='쇼핑' AND type='EXPENSE';
UPDATE accounts SET is_system=1, level=1, allow_posting=0
WHERE name='여가/취미' AND type='EXPENSE';

UPDATE accounts SET is_system=0, level=2, allow_posting=1
WHERE name='기초순자산' AND type='EQUITY';
UPDATE accounts SET is_system=0, level=2, allow_posting=1
WHERE name='기초자본(Opening Balance)' AND type='EQUITY';
