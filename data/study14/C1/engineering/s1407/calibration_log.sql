-- Test rig calibration history
-- source dataset: calibration_log; 16 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (1, 'P-40701', 20535);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (2, 'P-40716', 20601);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (3, 'P-40712', 20545);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (4, 'P-40705', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (5, 'P-40704', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (6, 'P-40706', 20617);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (7, 'P-40715', 20480);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (8, 'P-40703', 20547);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (9, 'P-40709', NULL);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (10, 'P-40710', 20530);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (11, 'P-40708', 20525);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (12, 'P-40707', 20629);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (13, 'P-40713', 20473);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (14, 'P-40711', 20595);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (15, 'P-40714', 20501);
INSERT INTO rig_calibration (row_seq, cmp_code, rig_cal_epd) VALUES (16, 'P-40702', 20486);
COMMIT;
