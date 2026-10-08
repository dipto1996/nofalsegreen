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
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (1, 'E-40204', 20808);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (2, 'E-40205', 20527);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (3, 'E-40209', NULL);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (4, 'E-40215', 20814);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (5, 'E-40213', 20662);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (6, 'E-40212', 20690);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (7, 'E-40208', 20637);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (8, 'E-40205', 20521);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (9, 'E-40201', 20669);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (10, 'E-40203', 20543);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (11, 'E-40206', 20702);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (12, 'E-40211', 20573);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (13, 'E-40216', 20865);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (14, 'E-40214', 20823);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (15, 'E-40202', 20733);
INSERT INTO i9_redo (row_seq, wkr_code, i9_redo_done_epd) VALUES (16, 'E-40210', NULL);
COMMIT;
