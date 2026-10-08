-- Dock scanner events
-- source dataset: warehouse_scans; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE dock_scanner_event (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    ord_code TEXT NOT NULL,  -- order reference
    scanner_hit_epd INTEGER  -- dock scanner recorded the delivery (epoch day)
);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (1, 'PO-40403', 20495);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (2, 'PO-40413', 20558);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (3, 'PO-40414', 20592);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (4, 'PO-40412', 20567);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (5, 'PO-40415', 20514);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (6, 'PO-40415', 20519);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (7, 'PO-40405', 20653);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (8, 'PO-40406', 20566);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (9, 'PO-40409', 20579);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (10, 'PO-40404', 20658);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (11, 'PO-40411', 20553);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (12, 'PO-40416', 20494);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (13, 'PO-40402', 20540);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (14, 'PO-40401', 20586);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (15, 'PO-40408', 20514);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES (16, 'PO-40410', 20654);
COMMIT;
