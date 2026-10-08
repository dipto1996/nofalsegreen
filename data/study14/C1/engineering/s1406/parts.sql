-- Component master
-- source dataset: parts; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE component_master (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    design_force_dan NUMERIC,  -- design target force, decanewtons
    qa_verdict_cd TEXT,  -- quality disposition
    rig_booking_epd INTEGER  -- booked test slot (epoch day)
);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (1, 'P-40603', 53200, 'Pass', 20768);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (2, 'P-40606', 14200, 'Pass', 21031);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (3, 'P-40614', 14200, 'Pass', 20799);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (4, 'P-40608', 24400, 'Pass', 20997);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (5, 'P-40611', 50800, 'Pass', 20751);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (6, 'P-40612', 41200, 'Pass', 20559);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (7, 'P-40616', 23800, 'Pass', 20963);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (8, 'P-40609', 50800, 'Pass', 21014);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (9, 'P-40601', 16600, 'Pass', 20907);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (10, 'P-40610', 26200, 'Pass', 20886);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (11, 'P-40604', 28600, 'Pass', 20816);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (12, 'P-40607', 49600, 'Pass', 20891);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (13, 'P-40613', 7600, 'Pass', 20726);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (14, 'P-40602', 49000, 'Pass', 20509);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (15, 'P-40605', 25600, 'Pass', 20788);
INSERT INTO component_master (row_seq, cmp_code, design_force_dan, qa_verdict_cd, rig_booking_epd) VALUES (16, 'P-40615', 14200, 'Pass', 20601);
COMMIT;
