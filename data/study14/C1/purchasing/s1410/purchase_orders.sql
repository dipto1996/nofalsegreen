-- Committed orders
-- source dataset: purchase_orders; 14 record(s); one VALUES tuple per record, in row_seq order
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
  (1, 'PO-41005', 13350000),
  (2, 'PO-41004', 12400000),
  (3, 'PO-41016', 5550000),
  (4, 'PO-41010', 18100000),
  (5, 'PO-41001', 7200000),
  (6, 'PO-41014', 850000),
  (7, 'PO-41013', 2000000),
  (8, 'PO-41015', 19050000);
INSERT INTO order_commitment (row_seq, ord_code, commit_cents) VALUES
  (9, 'PO-41009', 1500000),
  (10, 'PO-41007', 13050000),
  (11, 'PO-41008', 1000000),
  (12, 'PO-41011', 15550000),
  (13, 'PO-41012', 13800000),
  (14, 'PO-41006', 19250000);
COMMIT;
