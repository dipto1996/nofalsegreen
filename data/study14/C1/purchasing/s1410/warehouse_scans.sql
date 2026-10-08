-- Dock scanner events
-- source dataset: warehouse_scans; 17 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (1, 'PO-41013', 20483),
  (2, 'PO-41004', 20473),
  (3, 'PO-41015', 20542),
  (4, 'PO-41011', 20529),
  (5, 'PO-41002', 20585),
  (6, 'PO-41006', 20576),
  (7, 'PO-41003', 20584),
  (8, 'PO-41005', 20493);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (9, 'PO-41010', 20520),
  (10, 'PO-41001', 20637),
  (11, 'PO-41012', 20586),
  (12, 'PO-41014', 20513),
  (13, 'PO-41016', 20517),
  (14, 'PO-41008', 20573),
  (15, 'PO-41011', 20533),
  (16, 'PO-41007', 20587);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (17, 'PO-41009', 20566);
COMMIT;
