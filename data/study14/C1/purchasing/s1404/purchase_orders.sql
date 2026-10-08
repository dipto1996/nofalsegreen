-- Committed orders
-- source dataset: purchase_orders; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE order_commitment (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    ord_code TEXT NOT NULL,  -- order reference
    commit_cents NUMERIC  -- committed order value, US cents
);
INSERT INTO order_commitment (row_seq, ord_code, commit_cents) VALUES
  (1, 'PO-40412', 5850000),
  (2, 'PO-40406', 14250000),
  (3, 'PO-40405', 10200000),
  (4, 'PO-40407', 16050000),
  (5, 'PO-40414', 5850000),
  (6, 'PO-40411', 4200000),
  (7, 'PO-40404', 3250000),
  (8, 'PO-40416', 10150000);
INSERT INTO order_commitment (row_seq, ord_code, commit_cents) VALUES
  (9, 'PO-40413', 7950000),
  (10, 'PO-40409', 10500000),
  (11, 'PO-40403', 10600000),
  (12, 'PO-40410', 15650000),
  (13, 'PO-40402', 13600000),
  (14, 'PO-40401', 3550000),
  (15, 'PO-40408', 2700000),
  (16, 'PO-40415', 11250000);
COMMIT;
