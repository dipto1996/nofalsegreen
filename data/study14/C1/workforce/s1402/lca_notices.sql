-- Worksite LCA notice postings
-- source dataset: lca_notices; 14 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (1, 'E-40209', 20638, 20615);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (2, 'E-40204', 20653, 20640);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (3, 'E-40215', NULL, 20649);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (4, 'E-40205', 20544, 20532);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (5, 'E-40213', 20604, 20572);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (6, 'E-40208', 20587, 20563);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (7, 'E-40214', 20534, 20517);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (8, 'E-40212', 20543, 20531);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (9, 'E-40216', 20586, 20562);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (10, 'E-40207', 20484, 20471);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (11, 'E-40202', 20644, 20631);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (12, 'E-40210', 20611, 20600);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (13, 'E-40206', 20593, 20559);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_unpinned_epd, board_pinned_epd) VALUES (14, 'E-40201', 20512, 20499);
COMMIT;
