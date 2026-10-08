-- Department of Labor acknowledgements
-- source dataset: dol_receipts; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE agency_ack (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    agency_stamp_epd INTEGER  -- agency acknowledgement stamped (epoch day)
);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES
  (1, 'E-40912', 20538),
  (2, 'E-40901', 20659),
  (3, 'E-40911', 20530),
  (4, 'E-40914', 20571),
  (5, 'E-40909', 20618),
  (6, 'E-40910', 20666),
  (7, 'E-40907', 20570),
  (8, 'E-40907', 20566);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES
  (9, 'E-40902', 20655),
  (10, 'E-40905', 20556),
  (11, 'E-40906', 20512),
  (12, 'E-40904', 20590),
  (13, 'E-40913', NULL),
  (14, 'E-40908', 20602),
  (15, 'E-40903', 20548),
  (16, 'E-40916', 20623);
COMMIT;
