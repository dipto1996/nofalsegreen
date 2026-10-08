-- Remittance ledger
-- source dataset: payments; 15 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (1, 'PO-40504', 20531);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (2, 'PO-40505', 20662);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (3, 'PO-40516', 20562);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (4, 'PO-40509', 20566);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (5, 'PO-40515', 20539);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (6, 'PO-40502', 20651);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (7, 'PO-40512', 20612);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (8, 'PO-40507', 20564);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (9, 'PO-40514', 20538);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (10, 'PO-40511', 20476);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (11, 'PO-40501', 20632);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (12, 'PO-40510', 20640);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (13, 'PO-40508', 20505);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (14, 'PO-40513', 20466);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (15, 'PO-40503', 20536);
COMMIT;
