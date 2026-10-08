-- LCA submissions
-- source dataset: lca_filings; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE lca_lodgement (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    lca_lodge_epd INTEGER  -- LCA lodged with the agency (epoch day)
);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (1, 'E-40214', 20513);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (2, 'E-40203', 20480);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (3, 'E-40204', 20665);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (4, 'E-40202', 20638);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (5, 'E-40209', 20622);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (6, 'E-40201', NULL);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (7, 'E-40205', 20556);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (8, 'E-40207', 20496);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (9, 'E-40210', 20616);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (10, 'E-40213', 20577);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (11, 'E-40211', 20537);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (12, 'E-40216', 20544);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (13, 'E-40208', 20560);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (14, 'E-40215', 20636);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (15, 'E-40206', 20545);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (16, 'E-40212', NULL);
COMMIT;
