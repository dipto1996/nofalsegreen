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
    board_pinned_epd INTEGER,  -- notice pinned up at worksite (epoch day)
    board_unpinned_epd INTEGER  -- notice taken off the board (epoch day)
);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (1, 'E-40902', 20637, 20659);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (2, 'E-40903', 20562, 20590);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (3, 'E-40916', 20608, 20625);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (4, 'E-40912', 20537, 20565);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (5, 'E-40911', 20527, 20546);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (6, 'E-40910', 20647, 20679);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (7, 'E-40907', 20557, 20586);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (8, 'E-40908', 20602, 20616);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (9, 'E-40914', 20571, 20585);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (10, 'E-40901', 20636, 20650);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (11, 'E-40905', 20541, 20548);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (12, 'E-40906', 20487, 20517);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (13, 'E-40904', NULL, 20612);
INSERT INTO lca_board_notice (row_seq, wkr_code, board_pinned_epd, board_unpinned_epd) VALUES (14, 'E-40913', 20647, 20659);
COMMIT;
