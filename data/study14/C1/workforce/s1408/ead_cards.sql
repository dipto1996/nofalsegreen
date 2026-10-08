-- EAD card register
-- source dataset: ead_cards; 17 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE ead_card (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    wkr_code TEXT NOT NULL,  -- worker reference
    ead_lapse_epd INTEGER  -- EAD card lapses (epoch day)
);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (1, 'E-40807', 20764);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (2, 'E-40803', 20783);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (3, 'E-40815', 20665);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (4, 'E-40816', 20686);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (5, 'E-40814', 20802);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (6, 'E-40802', 20884);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (7, 'E-40811', 20603);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (8, 'E-40801', 20809);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (9, 'E-40805', 20728);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (10, 'E-40810', 20774);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (11, 'E-40812', 20584);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (12, 'E-40806', 20795);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (13, 'E-40804', 20931);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (14, 'E-40809', 20669);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (15, 'E-40813', 20695);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (16, 'E-40808', 20808);
INSERT INTO ead_card (row_seq, wkr_code, ead_lapse_epd) VALUES (17, 'E-40803', 20776);
COMMIT;
