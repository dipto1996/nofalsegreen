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
    rig_booking_epd INTEGER,  -- booked test slot (epoch day)
    qa_verdict_cd TEXT,  -- quality disposition
    design_force_dan NUMERIC  -- design target force, decanewtons
);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (1, 'P-40706', 20719, 'Pass', 33400);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (2, 'P-40708', 20627, 'Pass', 59800);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (3, 'P-40702', 20653, 'Pass', 9400);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (4, 'P-40713', 20880, 'Pass', 49000);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (5, 'P-40715', 20468, 'Pass', 29200);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (6, 'P-40707', 20893, 'Pass', 56200);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (7, 'P-40710', 20524, 'Pass', 19600);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (8, 'P-40711', 20951, 'Pass', 9400);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (9, 'P-40714', 20811, 'Pass', 28600);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (10, 'P-40716', 20565, 'Pass', 8200);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (11, 'P-40705', 20621, 'Pass', 13000);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (12, 'P-40704', 20856, 'Pass', 11200);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (13, 'P-40701', 20932, 'Pass', 21400);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (14, 'P-40712', 20923, 'Pass', 17200);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (15, 'P-40703', 20621, 'Pass', 58600);
INSERT INTO component_master (row_seq, cmp_code, rig_booking_epd, qa_verdict_cd, design_force_dan) VALUES (16, 'P-40709', 20588, 'Pass', 23800);
COMMIT;
