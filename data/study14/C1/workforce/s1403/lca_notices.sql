-- Worksite LCA notice postings
-- source dataset: lca_notices; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE lca_board_notice (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    board_unpinned_epd INTEGER,  -- notice taken off the board (epoch day)
    board_pinned_epd INTEGER  -- notice pinned up at worksite (epoch day)
);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES
  (1, 'E-40309', 20599, 20566),
  (2, 'E-40312', 20647, 20627),
  (3, 'E-40316', 20531, 20497),
  (4, 'E-40306', 20613, 20584),
  (5, 'E-40301', 20528, 20512),
  (6, 'E-40314', 20513, 20502),
  (7, 'E-40313', 20681, 20653),
  (8, 'E-40302', 20656, 20626);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES
  (9, 'E-40307', 20627, 20596),
  (10, 'E-40304', 20660, 20653),
  (11, 'E-40305', 20493, 20480),
  (12, 'E-40315', 20677, 20649),
  (13, 'E-40308', NULL, 20483),
  (14, 'E-40303', 20580, 20546),
  (15, 'E-40311', 20664, 20638),
  (16, 'E-40310', 20621, 20604);
COMMIT;
