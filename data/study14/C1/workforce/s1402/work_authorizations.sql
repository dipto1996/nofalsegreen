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
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (1, 'E-40203', 'EAD', 20551);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (2, 'E-40206', 'EAD', 20724);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (3, 'E-40211', 'EAD', 20596);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (4, 'E-40202', 'EAD', 20715);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (5, 'E-40216', 'EAD', 20845);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (6, 'E-40212', 'EAD', 20816);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (7, 'E-40214', 'EAD', 20913);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (8, 'E-40204', 'EAD', 20855);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (9, 'E-40205', 'EAD', 20642);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (10, 'E-40215', 'EAD', 20940);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (11, 'E-40213', 'EAD', 20765);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (12, 'E-40209', 'EAD', 20969);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (13, 'E-40214', 'EAD', 20928);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (14, 'E-40201', 'EAD', 20731);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (15, 'E-40210', 'EAD', 20863);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES (16, 'E-40208', 'EAD', 20716);
COMMIT;
