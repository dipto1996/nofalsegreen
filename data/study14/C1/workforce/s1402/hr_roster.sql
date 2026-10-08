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
    i9_redo_state TEXT,  -- state of the I-9 re-check
    lca_intended_lodge_epd INTEGER,  -- intended LCA submission (epoch day)
    lca_board_state TEXT  -- state of the worksite LCA posting
);
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd, lca_board_state) VALUES
  (1, 'E-40208', 21005, 'Complete', 20591, 'Posted'),
  (2, 'E-40211', 20659, 'Complete', 20524, 'Posted'),
  (3, 'E-40202', 20822, 'Complete', 20658, 'Posted'),
  (4, 'E-40207', 21235, 'Complete', 20488, 'Posted'),
  (5, 'E-40201', 20881, 'Complete', 20518, 'Posted'),
  (6, 'E-40212', 21215, 'Complete', 20560, 'Posted'),
  (7, 'E-40214', 21087, 'Complete', 20521, 'Posted'),
  (8, 'E-40204', 20948, 'Complete', 20652, 'Posted');
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, i9_redo_state, lca_intended_lodge_epd, lca_board_state) VALUES
  (9, 'E-40203', 20609, 'Complete', 20484, 'Posted'),
  (10, 'E-40215', 21201, 'Complete', 20666, 'Posted'),
  (11, 'E-40206', 21102, 'Complete', 20573, 'Posted'),
  (12, 'E-40205', 20806, 'Complete', 20561, 'Posted'),
  (13, 'E-40216', 21055, 'Complete', 20575, 'Posted'),
  (14, 'E-40210', 20946, 'Complete', 20611, 'Posted'),
  (15, 'E-40213', 20984, 'Complete', 20602, 'Posted'),
  (16, 'E-40209', 21086, 'Complete', 20637, 'Posted');
COMMIT;
