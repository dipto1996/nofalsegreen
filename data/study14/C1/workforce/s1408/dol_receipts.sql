-- Department of Labor acknowledgements
-- source dataset: dol_receipts; 15 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (1, 'E-40803', 20608);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (2, 'E-40806', 20638);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (3, 'E-40802', 20511);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (4, 'E-40810', 20503);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (5, 'E-40812', 20501);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (6, 'E-40807', NULL);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (7, 'E-40816', 20470);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (8, 'E-40811', 20538);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (9, 'E-40804', 20619);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (10, 'E-40815', 20604);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (11, 'E-40805', 20505);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (12, 'E-40814', 20471);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (13, 'E-40801', 20475);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (14, 'E-40813', 20612);
INSERT INTO agency_ack (row_seq, wkr_code, agency_stamp_epd) VALUES (15, 'E-40808', 20574);
COMMIT;
