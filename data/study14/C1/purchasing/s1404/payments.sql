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
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (1, 'PO-40401', 20602);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (2, 'PO-40416', 20485);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (3, 'PO-40408', 20501);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (4, 'PO-40415', 20534);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (5, 'PO-40402', 20556);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (6, 'PO-40409', 20590);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (7, 'PO-40413', 20554);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (8, 'PO-40411', 20576);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (9, 'PO-40405', 20657);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (10, 'PO-40410', 20660);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (11, 'PO-40414', 20592);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (12, 'PO-40412', 20561);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (13, 'PO-40404', 20669);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (14, 'PO-40406', 20562);
INSERT INTO remittance (row_seq, ord_code, funds_out_epd) VALUES (15, 'PO-40403', 20511);
COMMIT;
