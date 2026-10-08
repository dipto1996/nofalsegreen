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
  (1, 'PO-40506', 8350000),
  (2, 'PO-40514', 1900000),
  (3, 'PO-40512', 350000),
  (4, 'PO-40515', 14200000);
INSERT INTO order_commitment (row_seq, ord_code, commit_cents) VALUES
  (5, 'PO-40516', 17350000),
  (6, 'PO-40509', 6400000),
  (7, 'PO-40511', 15300000),
  (8, 'PO-40507', 6450000);
INSERT INTO order_commitment (row_seq, ord_code, commit_cents) VALUES
  (9, 'PO-40504', 17800000),
  (10, 'PO-40501', NULL),
  (11, 'PO-40503', 6900000),
  (12, 'PO-40502', 4050000);
INSERT INTO order_commitment (row_seq, ord_code, commit_cents) VALUES
  (13, 'PO-40505', 19200000),
  (14, 'PO-40510', 2550000),
  (15, 'PO-40508', 12850000),
  (16, 'PO-40513', 6950000);
COMMIT;
