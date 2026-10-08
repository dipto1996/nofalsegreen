-- Supplier bills
-- source dataset: invoices; 14 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE supplier_bill (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    ord_code TEXT NOT NULL,  -- order reference
    pay_deadline_epd INTEGER,  -- latest settle day on the bill (epoch day)
    billed_cents NUMERIC,  -- supplier bill total, US cents
    billed_unit_ct NUMERIC  -- units on the supplier bill
);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_cents, billed_unit_ct) VALUES
  (1, 'PO-40415', 20515, 11400000, 129),
  (2, 'PO-40403', 20529, 10710000, 83),
  (3, 'PO-40408', 20522, 2250000, 379),
  (4, 'PO-40412', 20583, 5400000, NULL),
  (5, 'PO-40401', 20609, 3800000, 446),
  (6, 'PO-40410', 20657, 15450000, 203),
  (7, 'PO-40413', 20566, 8200000, 250),
  (8, 'PO-40406', 20572, 14300000, 92);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_cents, billed_unit_ct) VALUES
  (9, 'PO-40402', 20551, 14100000, NULL),
  (10, 'PO-40404', 20689, 3000000, 292),
  (11, 'PO-40411', 20566, 3800000, 401),
  (12, 'PO-40409', 20591, 10150000, 387),
  (13, 'PO-40416', 20485, 10150000, 297),
  (14, 'PO-40403', 20529, 10200000, 83);
COMMIT;
