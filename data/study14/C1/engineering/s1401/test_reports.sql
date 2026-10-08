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
  (1, 'P-40105', 42000, 20923),
  (2, 'P-40108', 49400, 20649),
  (3, 'P-40112', 51700, 20955),
  (4, 'P-40111', 16500, 20521),
  (5, 'P-40103', 19400, 21052),
  (6, 'P-40109', 57000, 20771),
  (7, 'P-40113', 14200, 20608),
  (8, 'P-40105', 42000, 20929);
INSERT INTO inhouse_break_test (row_seq, cmp_code, inhouse_break_dan, inhouse_break_epd) VALUES
  (9, 'P-40102', 8800, 20893),
  (10, 'P-40114', 45100, 20827),
  (11, 'P-40115', 5700, 20798),
  (12, 'P-40106', 25400, 20853),
  (13, 'P-40104', 12400, 21015),
  (14, 'P-40116', 24000, 20999),
  (15, 'P-40107', 54500, 21049),
  (16, 'P-40101', 15300, 20861);
INSERT INTO inhouse_break_test (row_seq, cmp_code, inhouse_break_dan, inhouse_break_epd) VALUES
  (17, 'P-40104', 11800, 21015);
COMMIT;
