-- Remittance ledger
-- source dataset: payments; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE remittance (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    ord_code TEXT NOT NULL,  -- order reference
    funds_out_epd INTEGER  -- funds sent (epoch day)
);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES
  (1, 'PO-41009', 20558),
  (2, 'PO-41004', 20463),
  (3, 'PO-41010', 20546),
  (4, 'PO-41001', 20644);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES
  (5, 'PO-41007', 20618),
  (6, 'PO-41011', 20531),
  (7, 'PO-41006', 20585),
  (8, 'PO-41012', 20602);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES
  (9, 'PO-41014', 20503),
  (10, 'PO-41013', NULL),
  (11, 'PO-41016', 20537),
  (12, 'PO-41003', 20595);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES
  (13, 'PO-41005', 20506),
  (14, 'PO-41008', 20564),
  (15, 'PO-41002', 20592),
  (16, 'PO-41015', 20535);
COMMIT;
