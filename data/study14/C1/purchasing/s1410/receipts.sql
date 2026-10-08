-- Goods-in notes
-- source dataset: receipts; 15 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE goods_in_note (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    ord_code TEXT NOT NULL,  -- order reference
    dock_unit_ct NUMERIC,  -- units counted at goods-in
    goods_in_epd INTEGER  -- goods booked in (epoch day)
);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES
  (1, 'PO-41005', 107, 20493),
  (2, 'PO-41012', 156, 20586),
  (3, 'PO-41013', 508, 20483),
  (4, 'PO-41016', 139, 20517),
  (5, 'PO-41006', 12, 20576),
  (6, 'PO-41009', 83, 20558),
  (7, 'PO-41010', 396, 20524),
  (8, 'PO-41007', 97, 20587);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES
  (9, 'PO-41010', 396, 20520),
  (10, 'PO-41014', 231, 20513),
  (11, 'PO-41002', 3, 20585),
  (12, 'PO-41015', 83, NULL),
  (13, 'PO-41004', 285, 20473),
  (14, 'PO-41011', 433, 20529),
  (15, 'PO-41008', 13, 20573);
COMMIT;
