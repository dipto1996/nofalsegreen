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
    qa_verdict_cd TEXT,  -- quality disposition
    rig_booking_epd INTEGER,  -- booked test slot (epoch day)
    design_force_dan NUMERIC  -- design target force, decanewtons
);
INSERT INTO component_master (row_seq, cmp_code, qa_verdict_cd, rig_booking_epd, design_force_dan) VALUES
  (1, 'P-40104', 'Pass', 21007, 13600),
  (2, 'P-40109', 'Pass', 20764, 56200),
  (3, 'P-40101', 'Pass', 20859, 16600),
  (4, 'P-40115', 'Pass', 20797, 8200);
INSERT INTO component_master (row_seq, cmp_code, qa_verdict_cd, rig_booking_epd, design_force_dan) VALUES
  (5, 'P-40111', 'Pass', 20514, 17200),
  (6, 'P-40105', 'Pass', 20918, 42400),
  (7, 'P-40113', 'Pass', 20599, 15400),
  (8, 'P-40108', 'Pass', 20643, 49600);
INSERT INTO component_master (row_seq, cmp_code, qa_verdict_cd, rig_booking_epd, design_force_dan) VALUES
  (9, 'P-40116', 'Pass', 20995, 25000),
  (10, 'P-40114', 'Pass', 20823, 44800),
  (11, 'P-40103', 'Pass', 21048, 21400),
  (12, 'P-40102', 'Pass', 20892, 11800);
INSERT INTO component_master (row_seq, cmp_code, qa_verdict_cd, rig_booking_epd, design_force_dan) VALUES
  (13, 'P-40112', 'Pass', 20954, 50800),
  (14, 'P-40106', 'Pass', 20843, 24400),
  (15, 'P-40107', 'Pass', 21044, 57400),
  (16, 'P-40110', 'Pass', 20737, 49000);
COMMIT;
