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
  (1, 'E-40903', 20677),
  (2, 'E-40906', 20802),
  (3, 'E-40905', 20866),
  (4, 'E-40912', 20783),
  (5, 'E-40901', 20753),
  (6, 'E-40915', 20604),
  (7, 'E-40910', 20935),
  (8, 'E-40916', 20753);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES
  (9, 'E-40913', 20960),
  (10, 'E-40911', 20755),
  (11, 'E-40908', 20727),
  (12, 'E-40904', 20649),
  (13, 'E-40914', 20809),
  (14, 'E-40909', 20865),
  (15, 'E-40907', 20766),
  (16, 'E-40902', 20861);
COMMIT;
