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
    eligibility_doc_lapse_epd INTEGER,  -- eligibility document lapses (epoch day)
    eligibility_doc_kind TEXT  -- kind of eligibility document
);
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_lapse_epd, eligibility_doc_kind) VALUES
  (1, 'E-40803', 20776, 'EAD'),
  (2, 'E-40802', 20884, 'EAD'),
  (3, 'E-40811', 20603, 'EAD'),
  (4, 'E-40816', 20686, 'EAD');
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_lapse_epd, eligibility_doc_kind) VALUES
  (5, 'E-40806', 20795, 'EAD'),
  (6, 'E-40810', 20774, 'EAD'),
  (7, 'E-40801', 20809, 'EAD'),
  (8, 'E-40811', 20610, 'EAD');
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_lapse_epd, eligibility_doc_kind) VALUES
  (9, 'E-40812', 20584, 'EAD'),
  (10, 'E-40804', 20931, 'EAD'),
  (11, 'E-40815', 20665, 'EAD'),
  (12, 'E-40805', NULL, 'EAD');
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_lapse_epd, eligibility_doc_kind) VALUES
  (13, 'E-40814', 20802, 'EAD'),
  (14, 'E-40813', 20695, 'EAD'),
  (15, 'E-40808', 20808, 'EAD'),
  (16, 'E-40807', 20764, 'EAD');
INSERT INTO eligibility_doc (row_seq, wkr_code, eligibility_doc_lapse_epd, eligibility_doc_kind) VALUES
  (17, 'E-40809', 20669, 'EAD');
COMMIT;
