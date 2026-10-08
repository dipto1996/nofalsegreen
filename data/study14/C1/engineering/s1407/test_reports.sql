-- In-house break tests
-- source dataset: test_reports; 17 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE inhouse_break_test (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    inhouse_break_dan NUMERIC,  -- breaking force seen in-house, decanewtons
    inhouse_break_epd INTEGER  -- in-house break test run (epoch day)
);
INSERT INTO inhouse_break_test (row_seq, cmp_code, inhouse_break_dan, inhouse_break_epd) VALUES
  (1, 'P-40702', 7100, 20661),
  (2, 'P-40708', 57900, 20630),
  (3, 'P-40708', 57900, 20638),
  (4, 'P-40701', 21200, 20939),
  (5, 'P-40713', 47800, 20883),
  (6, 'P-40703', 56000, 20629),
  (7, 'P-40709', 24800, 20596),
  (8, 'P-40711', 8400, 20960);
INSERT INTO inhouse_break_test (row_seq, cmp_code, inhouse_break_dan, inhouse_break_epd) VALUES
  (9, 'P-40701', 20200, 20939),
  (10, 'P-40705', 13400, 20623),
  (11, 'P-40714', 27000, 20819),
  (12, 'P-40704', 11800, 20857),
  (13, 'P-40707', 55100, 20897),
  (14, 'P-40716', 6600, 20573),
  (15, 'P-40706', 34400, 20723),
  (16, 'P-40712', 14400, 20928);
INSERT INTO inhouse_break_test (row_seq, cmp_code, inhouse_break_dan, inhouse_break_epd) VALUES
  (17, 'P-40715', 28800, 20475);
COMMIT;
