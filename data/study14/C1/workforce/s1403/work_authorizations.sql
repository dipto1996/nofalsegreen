-- Employment eligibility documents held
-- source dataset: work_authorizations; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE eligibility_doc (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    eligibility_doc_kind TEXT,  -- kind of eligibility document
    eligibility_doc_lapse_epd INTEGER  -- eligibility document lapses (epoch day)
);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (1, 'E-40309', 'EAD', NULL);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (2, 'E-40311', 'EAD', 20957);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (3, 'E-40315', 'EAD', 20864);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (4, 'E-40313', 'EAD', 20862);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (5, 'E-40314', 'EAD', 20739);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (6, 'E-40302', 'EAD', 21016);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (7, 'E-40312', 'EAD', 20725);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (8, 'E-40305', 'EAD', 20660);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (9, 'E-40304', 'EAD', 20819);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (10, 'E-40307', 'EAD', 20717);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (11, 'E-40306', 'EAD', 20902);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (12, 'E-40310', 'EAD', 20950);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (13, 'E-40308', 'EAD', 20883);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (14, 'E-40315', 'EAD', 20850);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (15, 'E-40303', 'EAD', 20718);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (16, 'E-40316', 'EAD', 20724);
COMMIT;
