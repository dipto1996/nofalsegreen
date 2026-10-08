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
    lca_board_state TEXT,  -- state of the worksite LCA posting
    immig_lapse_epd INTEGER,  -- immigration status lapses (epoch day)
    i9_redo_state TEXT,  -- state of the I-9 re-check
    lca_intended_lodge_epd INTEGER  -- intended LCA submission (epoch day)
);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (1, 'E-40807', 'Posted', 21091, 'Complete', 20513);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (2, 'E-40801', 'Posted', 20898, 'Complete', 20476);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (3, 'E-40808', 'Posted', 21158, 'Complete', 20596);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (4, 'E-40811', 'Posted', 20716, 'Complete', 20553);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (5, 'E-40816', 'Posted', 20918, 'Complete', 20489);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (6, 'E-40810', 'Posted', 21013, 'Complete', 20519);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (7, 'E-40809', 'Posted', 20712, 'Complete', 20558);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (8, 'E-40804', 'Posted', 21213, 'Complete', 20620);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (9, 'E-40815', 'Posted', 21023, 'Complete', 20606);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (10, 'E-40803', 'Posted', 20974, 'Complete', 20596);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (11, 'E-40806', 'Posted', 20851, 'Complete', 20628);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (12, 'E-40802', 'Posted', 21228, 'Complete', 20546);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (13, 'E-40805', 'Posted', 20897, 'Complete', 20504);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (14, 'E-40814', 'Posted', 20877, 'Complete', 20485);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (15, 'E-40813', 'Posted', 20917, 'Complete', 20629);
INSERT INTO staff_master (row_seq, wkr_code, lca_board_state, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd) VALUES (16, 'E-40812', 'Posted', 20746, 'Complete', 20521);
COMMIT;
