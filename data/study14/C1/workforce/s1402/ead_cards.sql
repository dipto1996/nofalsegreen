-- EAD card register
-- source dataset: ead_cards; 16 record(s); one VALUES tuple per record, in row_seq order
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
  (1, 'E-40203', 20551),
  (2, 'E-40216', 20845),
  (3, 'E-40206', 20734),
  (4, 'E-40211', 20596);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES
  (5, 'E-40208', 20716),
  (6, 'E-40210', 20863),
  (7, 'E-40206', 20724),
  (8, 'E-40209', 20969);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES
  (9, 'E-40214', 20913),
  (10, 'E-40212', 20816),
  (11, 'E-40215', 20940),
  (12, 'E-40204', 20855);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES
  (13, 'E-40213', 20765),
  (14, 'E-40202', 20715),
  (15, 'E-40201', 20731),
  (16, 'E-40205', 20642);
COMMIT;
