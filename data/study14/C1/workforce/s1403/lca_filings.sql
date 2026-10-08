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
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES
  (1, 'E-40313', 20640),
  (2, 'E-40310', 20601),
  (3, 'E-40316', 20493),
  (4, 'E-40314', 20507),
  (5, 'E-40301', 20526),
  (6, 'E-40303', 20566),
  (7, 'E-40305', 20497),
  (8, 'E-40307', 20579);
INSERT INTO lca_lodgement (row_seq, wkr_code, lca_lodge_epd) VALUES
  (9, 'E-40311', 20635),
  (10, 'E-40306', 20587),
  (11, 'E-40315', 20639),
  (12, 'E-40309', 20552),
  (13, 'E-40302', 20609),
  (14, 'E-40308', 20485),
  (15, 'E-40312', 20609),
  (16, 'E-40304', NULL);
COMMIT;
