-- Design specification extracts
-- source dataset: spec_sheets; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE design_spec (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    cmp_code TEXT NOT NULL,  -- component reference
    floor_force_dan NUMERIC  -- required minimum breaking force, decanewtons
);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (1, 'P-40101', 13000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (2, 'P-40107', 47000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (3, 'P-40108', 40500);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (4, 'P-40111', 13500);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (5, 'P-40104', 10500);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (6, 'P-40106', 19500);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (7, 'P-40102', 9000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (8, 'P-40114', 36500);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (9, 'P-40103', 17000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (10, 'P-40116', 20000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (11, 'P-40105', 34500);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (12, 'P-40113', 12000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (13, 'P-40103', 17800);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (14, 'P-40115', 6000);
INSERT INTO design_spec (row_seq, cmp_code, floor_force_dan) VALUES (15, 'P-40112', NULL);
COMMIT;
