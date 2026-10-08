-- Worksite LCA notice postings
-- source dataset: lca_notices; 15 record(s); one VALUES tuple per record, in row_seq order
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
    board_pinned_epd INTEGER,  -- notice pinned up at worksite (epoch day)
    board_unpinned_epd INTEGER  -- notice taken off the board (epoch day)
);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES
  (1, 'E-40804', 20607, 20619),
  (2, 'E-40807', 20495, 20508),
  (3, 'E-40805', 20484, 20510),
  (4, 'E-40802', 20522, 20546);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES
  (5, 'E-40803', 20594, 20628),
  (6, 'E-40806', 20611, 20644),
  (7, 'E-40814', 20467, 20487),
  (8, 'E-40808', 20572, 20590);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES
  (9, 'E-40816', 20477, 20506),
  (10, 'E-40813', 20607, 20626),
  (11, 'E-40801', 20475, 20489),
  (12, 'E-40810', 20503, 20517);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES
  (13, 'E-40811', 20533, 20544),
  (14, 'E-40815', 20583, 20592),
  (15, 'E-40812', 20514, NULL);
COMMIT;
