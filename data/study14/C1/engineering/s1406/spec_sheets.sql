-- Design specification extracts
-- source dataset: spec_sheets; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE design_spec (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    floor_force_dan NUMERIC  -- required minimum breaking force, decanewtons
);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES
  (1, 'P-40604', 23000),
  (2, 'P-40602', 40000),
  (3, 'P-40614', 11000),
  (4, 'P-40601', NULL),
  (5, 'P-40616', 19000),
  (6, 'P-40605', 20500),
  (7, 'P-40612', 33500),
  (8, 'P-40613', 5800);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES
  (9, 'P-40611', 41500),
  (10, 'P-40603', 43500),
  (11, 'P-40606', 11000),
  (12, 'P-40607', 40500),
  (13, 'P-40615', 11000),
  (14, 'P-40610', 21000),
  (15, 'P-40613', 5500);
COMMIT;
