-- Test rig calibration history
-- source dataset: calibration_log; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE rig_calibration (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    rig_cal_epd INTEGER  -- test rig calibrated (epoch day)
);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (1, 'P-40109', 20607);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (2, 'P-40102', 20603);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (3, 'P-40108', 20528);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (4, 'P-40105', 20513);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (5, 'P-40104', 20632);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (6, 'P-40101', 20496);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (7, 'P-40110', 20625);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (8, 'P-40115', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (9, 'P-40111', 20537);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (10, 'P-40103', 20641);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (11, 'P-40116', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (12, 'P-40107', 20656);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (13, 'P-40112', 20643);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (14, 'P-40106', 20484);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (15, 'P-40113', 20610);
COMMIT;
