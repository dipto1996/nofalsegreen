-- External laboratory certificates
-- source dataset: lab_certificates; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE lab_cert (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    lab_break_dan NUMERIC,  -- breaking force attested by the lab, decanewtons
    lab_break_epd INTEGER  -- laboratory ran the trial (epoch day)
);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (1, 'P-40708', 57900, 20630);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (2, 'P-40715', 28800, 20475);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (3, 'P-40701', 20200, 20939);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (4, 'P-40706', 34400, 20723);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (5, 'P-40703', 56000, 20629);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (6, 'P-40709', 24800, 20596);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (7, 'P-40702', 7100, 20661);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (8, 'P-40712', 14400, 20928);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (9, 'P-40711', NULL, 20960);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (10, 'P-40716', 6600, 20587);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (11, 'P-40707', 55100, 20897);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (12, 'P-40705', 13400, 20623);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (13, 'P-40713', 47800, 20883);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (14, 'P-40714', 27000, 20819);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_dan, lab_break_epd) VALUES (15, 'P-40704', 11800, 20857);
COMMIT;
