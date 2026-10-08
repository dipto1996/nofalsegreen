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
    lab_break_epd INTEGER,  -- laboratory ran the trial (epoch day)
    lab_break_dan NUMERIC  -- breaking force attested by the lab, decanewtons
);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (1, 'P-40106', 20853, NULL);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (2, 'P-40101', 20861, 14600);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (3, 'P-40114', 20827, 45100);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (4, 'P-40111', 20521, 16500);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (5, 'P-40104', 21015, 11800);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (6, 'P-40105', 20923, 42000);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (7, 'P-40109', 20771, 57000);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (8, 'P-40108', 20649, 49400);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (9, 'P-40103', 21052, 19400);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (10, 'P-40115', 20798, 5700);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (11, 'P-40102', 20893, 8800);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (12, 'P-40112', 20955, 51700);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (13, 'P-40107', 21049, 54500);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (14, 'P-40116', 20999, 24000);
INSERT INTO lab_cert (row_seq, cmp_code, lab_break_epd, lab_break_dan) VALUES (15, 'P-40113', 20608, 14200);
COMMIT;
