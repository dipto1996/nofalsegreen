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
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (1, 'P-40613', 20553);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (2, 'P-40614', 20619);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (3, 'P-40610', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (4, 'P-40606', 20626);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (5, 'P-40616', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (6, 'P-40611', 20622);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (7, 'P-40602', 20538);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (8, 'P-40601', 20507);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (9, 'P-40607', 20505);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (10, 'P-40603', 20497);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (11, 'P-40605', 20559);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (12, 'P-40612', 20568);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (13, 'P-40609', 20604);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (14, 'P-40608', 20613);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (15, 'P-40604', 20543);
COMMIT;
