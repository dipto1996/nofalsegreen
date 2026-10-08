-- Staff master list
-- source dataset: hr_roster; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE staff_master (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    immig_lapse_epd INTEGER,  -- immigration status lapses (epoch day)
    lca_intended_lodge_epd INTEGER,  -- intended LCA submission (epoch day)
    lca_board_state TEXT,  -- state of the worksite LCA posting
    i9_redo_state TEXT  -- state of the I-9 re-check
);
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (1, 'E-40901', 20816, 20646, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (2, 'E-40908', 21035, 20632, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (3, 'E-40910', 21144, 20650, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (4, 'E-40916', 20990, 20624, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (5, 'E-40906', 21057, 20508, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (6, 'E-40913', 21325, 20676, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (7, 'E-40914', 20972, 20599, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (8, 'E-40903', 20952, 20570, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (9, 'E-40907', 20944, 20573, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (10, 'E-40905', 21050, 20568, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (11, 'E-40912', 21014, 20565, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (12, 'E-40911', 20809, 20549, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (13, 'E-40904', 20695, 20599, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (14, 'E-40902', 21088, 20644, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (15, 'E-40909', 21030, 20600, 'Posted', 'Complete');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, lca_intended_lodge_epd, lca_board_state, i9_redo_state) VALUES (16, 'E-40915', 20868, 20523, 'Posted', 'Complete');
COMMIT;
