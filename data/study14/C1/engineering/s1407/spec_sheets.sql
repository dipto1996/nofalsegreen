-- Design specification extracts
-- source dataset: spec_sheets; 14 record(s); one VALUES tuple per record, in row_seq order
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
  (1, 'P-40707', 46000),
  (2, 'P-40704', 8500),
  (3, 'P-40716', 6000),
  (4, 'P-40709', 19000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES
  (5, 'P-40715', 23500),
  (6, 'P-40711', 7000),
  (7, 'P-40702', 7000),
  (8, 'P-40708', 49000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES
  (9, 'P-40714', 24200),
  (10, 'P-40701', 17000),
  (11, 'P-40703', 48000),
  (12, 'P-40705', 10000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES
  (13, 'P-40714', 23000),
  (14, 'P-40713', 40000);
COMMIT;
