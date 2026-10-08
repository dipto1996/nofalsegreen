-- LCA submissions
-- source dataset: lca_filings; 15 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (1, 'E-40913', NULL);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (2, 'E-40912', 20538);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (3, 'E-40916', 20623);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (4, 'E-40902', 20655);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (5, 'E-40911', 20530);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (6, 'E-40907', 20566);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (7, 'E-40909', 20618);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (8, 'E-40903', 20548);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (9, 'E-40904', 20590);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (10, 'E-40901', 20659);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (11, 'E-40908', 20602);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (12, 'E-40906', 20512);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (13, 'E-40914', 20571);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (14, 'E-40910', 20666);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES (15, 'E-40905', 20556);
COMMIT;
