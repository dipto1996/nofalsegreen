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
  (1, 'E-40210', 20616),
  (2, 'E-40215', 20636),
  (3, 'E-40204', 20665),
  (4, 'E-40212', NULL);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES
  (5, 'E-40211', 20537),
  (6, 'E-40216', 20544),
  (7, 'E-40214', 20513),
  (8, 'E-40208', 20573);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES
  (9, 'E-40213', 20577),
  (10, 'E-40207', 20496),
  (11, 'E-40202', 20638),
  (12, 'E-40203', 20480);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES
  (13, 'E-40206', 20545),
  (14, 'E-40201', 20507),
  (15, 'E-40209', 20622),
  (16, 'E-40205', 20556);
COMMIT;
