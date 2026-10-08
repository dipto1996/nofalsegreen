-- External laboratory certificates
-- source dataset: lab_certificates; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE lab_cert (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    lab_break_epd INTEGER,  -- laboratory ran the trial (epoch day)
    lab_break_dan NUMERIC  -- breaking force attested by the lab, decanewtons
);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES
  (1, 'P-40609', 21018, 48300),
  (2, 'P-40605', 20790, 23300),
  (3, 'P-40604', 20819, 29000),
  (4, 'P-40614', 20801, 15000),
  (5, 'P-40607', 20894, 48400),
  (6, 'P-40610', 20891, 23300),
  (7, 'P-40611', 20766, 50600),
  (8, 'P-40603', 20774, 50900);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES
  (9, 'P-40608', 21001, 23600),
  (10, 'P-40616', 20970, 24100),
  (11, 'P-40601', 20914, 16500),
  (12, 'P-40612', 20562, 41800),
  (13, 'P-40613', 20727, 8200),
  (14, 'P-40606', 21033, 11600),
  (15, 'P-40602', 20519, 48000);
COMMIT;
