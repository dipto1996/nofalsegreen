-- I-9 re-check events
-- source dataset: reverifications; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE i9_redo (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    i9_redo_done_epd INTEGER  -- I-9 re-check carried out (epoch day)
);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES
  (1, 'E-40811', 20486),
  (2, 'E-40807', 20765),
  (3, 'E-40812', 20574),
  (4, 'E-40810', 20660);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES
  (5, 'E-40815', NULL),
  (6, 'E-40803', 20739),
  (7, 'E-40801', 20719),
  (8, 'E-40805', 20696);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES
  (9, 'E-40806', 20793),
  (10, 'E-40814', 20653),
  (11, 'E-40813', 20712),
  (12, 'E-40809', 20680);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES
  (13, 'E-40814', 20668),
  (14, 'E-40804', NULL),
  (15, 'E-40808', 20816);
COMMIT;
