-- EAD card register
-- source dataset: ead_cards; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE ead_card (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    ead_lapse_epd INTEGER  -- EAD card lapses (epoch day)
);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES
  (1, 'E-40315', 20850),
  (2, 'E-40308', 20883),
  (3, 'E-40302', 21016),
  (4, 'E-40311', 20957),
  (5, 'E-40313', 20862),
  (6, 'E-40306', 20902),
  (7, 'E-40316', 20724),
  (8, 'E-40307', 20717);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES
  (9, 'E-40310', 20950),
  (10, 'E-40312', 20725),
  (11, 'E-40304', 20819),
  (12, 'E-40305', 20660),
  (13, 'E-40309', 20923),
  (14, 'E-40303', 20718),
  (15, 'E-40314', 20739);
COMMIT;
