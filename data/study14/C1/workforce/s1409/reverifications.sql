-- I-9 re-check events
-- source dataset: reverifications; 16 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (1, 'E-40912', 20807);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (2, 'E-40913', 20965);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (3, 'E-40906', 20815);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (4, 'E-40904', 20567);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (5, 'E-40915', 20604);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (6, 'E-40911', 20628);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (7, 'E-40914', 20719);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (8, 'E-40908', 20727);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (9, 'E-40902', 20792);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (10, 'E-40910', NULL);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (11, 'E-40909', 20875);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (12, 'E-40903', NULL);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (13, 'E-40902', 20803);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (14, 'E-40907', 20680);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (15, 'E-40905', 20827);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (16, 'E-40916', 20768);
COMMIT;
