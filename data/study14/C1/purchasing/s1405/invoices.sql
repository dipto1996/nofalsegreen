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
  (1, 'PO-40502', 20652, 266, 4350000),
  (2, 'PO-40512', 20615, 406, 0),
  (3, 'PO-40516', 20575, 292, 17200000),
  (4, 'PO-40511', 20490, 123, 14900000);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_unit_ct, billed_cents) VALUES
  (5, 'PO-40508', NULL, 380, 12700000),
  (6, 'PO-40504', 20543, 328, 17550000),
  (7, 'PO-40507', 20596, 247, 6950000),
  (8, 'PO-40514', 20535, 397, 2000000);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_unit_ct, billed_cents) VALUES
  (9, 'PO-40510', 20634, 128, 2550000),
  (10, 'PO-40503', NULL, 408, 6600000),
  (11, 'PO-40509', NULL, 41, 6400000),
  (12, 'PO-40513', 20468, 460, 6450000);
INSERT INTO supplier_bill (row_seq, ord_code, pay_deadline_epd, billed_unit_ct, billed_cents) VALUES
  (13, 'PO-40513', 20468, 460, 6772500),
  (14, 'PO-40515', 20546, 492, 13750000),
  (15, 'PO-40505', 20674, 241, 18900000),
  (16, 'PO-40501', 20633, 458, 5900000);
COMMIT;
