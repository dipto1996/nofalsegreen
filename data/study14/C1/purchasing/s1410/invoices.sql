-- Supplier bills
-- source dataset: invoices; 16 record(s); one VALUES tuple per record, in row_seq order
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
    billed_unit_ct NUMERIC,  -- units on the supplier bill
    billed_cents NUMERIC  -- supplier bill total, US cents
);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_unit_ct, billed_cents) VALUES
  (1, 'PO-41005', 20533, 100, 13200000),
  (2, 'PO-41006', 20576, 12, 19250000),
  (3, 'PO-41012', NULL, 164, 13300000),
  (4, 'PO-41001', 20652, 107, 7450000),
  (5, 'PO-41008', 20595, 19, 750000),
  (6, 'PO-41015', 20572, 87, 19150000),
  (7, 'PO-41005', 20523, 100, 13200000),
  (8, 'PO-41016', 20525, 125, 5350000);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_unit_ct, billed_cents) VALUES
  (9, 'PO-41004', NULL, 278, 12150000),
  (10, 'PO-41011', 20547, 441, 15050000),
  (11, 'PO-41010', 20540, 396, 18600000),
  (12, 'PO-41009', 20558, 90, 1500000),
  (13, 'PO-41002', 20607, 10, 14850000),
  (14, 'PO-41007', NULL, 101, 12600000),
  (15, 'PO-41013', 20493, 496, 1650000),
  (16, 'PO-41014', 20519, 219, 400000);
COMMIT;
