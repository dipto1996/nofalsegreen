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
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (1, 'PO-40504', 20517),
  (2, 'PO-40516', 20557),
  (3, 'PO-40501', 20631),
  (4, 'PO-40502', 20638);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (5, 'PO-40511', 20480),
  (6, 'PO-40507', 20568),
  (7, 'PO-40515', 20525),
  (8, 'PO-40505', 20647);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (9, 'PO-40505', 20661),
  (10, 'PO-40509', 20566),
  (11, 'PO-40513', 20464),
  (12, 'PO-40510', 20630);
INSERT INTO dock_scanner_event (row_seq, ord_code, scanner_hit_epd) VALUES
  (13, 'PO-40512', 20592),
  (14, 'PO-40514', 20531),
  (15, 'PO-40508', 20493),
  (16, 'PO-40503', 20550);
COMMIT;
