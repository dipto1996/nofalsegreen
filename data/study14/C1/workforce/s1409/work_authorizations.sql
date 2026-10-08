-- Employment eligibility documents held
-- source dataset: work_authorizations; 17 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES
  (1, 'E-40914', 'EAD', 20809),
  (2, 'E-40907', 'EAD', 20766),
  (3, 'E-40906', 'EAD', 20802),
  (4, 'E-40908', 'EAD', 20727);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES
  (5, 'E-40901', 'EAD', 20753),
  (6, 'E-40902', 'EAD', 20861),
  (7, 'E-40916', 'EAD', NULL),
  (8, 'E-40909', 'EAD', 20865);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES
  (9, 'E-40913', 'EAD', 20960),
  (10, 'E-40908', 'EAD', 20733),
  (11, 'E-40903', 'EAD', 20677),
  (12, 'E-40912', 'EAD', 20783);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES
  (13, 'E-40911', 'EAD', 20755),
  (14, 'E-40910', 'EAD', 20935),
  (15, 'E-40915', 'EAD', 20604),
  (16, 'E-40904', 'EAD', 20649);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_kind, eligibility_doc_lapse_epd) VALUES
  (17, 'E-40905', 'EAD', 20855);
COMMIT;
