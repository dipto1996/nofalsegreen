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
    lca_board_state TEXT,  -- state of the worksite LCA posting
    lca_intended_lodge_epd INTEGER  -- intended LCA submission (epoch day)
);
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, i9_redo_state, lca_board_state, lca_intended_lodge_epd) VALUES
  (1, 'E-40307', 20854, 'Complete', 'Posted', 20616),
  (2, 'E-40312', 20857, 'Complete', 'Posted', 20630),
  (3, 'E-40316', 20884, 'Complete', 'Posted', 20521),
  (4, 'E-40315', 20994, 'Complete', 'Posted', 20667),
  (5, 'E-40311', 21065, 'Complete', 'Posted', 20646),
  (6, 'E-40308', 21106, 'Complete', 'Posted', 20510),
  (7, 'E-40303', 20835, 'Complete', 'Posted', 20573),
  (8, 'E-40302', 21056, 'Complete', 'Posted', 20651);
INSERT INTO staff_master (row_seq, wkr_code, immig_lapse_epd, i9_redo_state, lca_board_state, lca_intended_lodge_epd) VALUES
  (9, 'E-40305', 21054, 'Complete', 'Posted', 20498),
  (10, 'E-40309', 21090, 'Complete', 'Posted', 20595),
  (11, 'E-40304', 21197, 'Complete', 'Posted', 20664),
  (12, 'E-40301', 20832, 'Complete', 'Posted', 20542),
  (13, 'E-40313', 21262, 'Complete', 'Posted', 20667),
  (14, 'E-40306', 21090, 'Complete', 'Posted', 20587),
  (15, 'E-40314', 20854, 'Complete', 'Posted', 20510),
  (16, 'E-40310', 21103, 'Complete', 'Posted', 20607);
COMMIT;
