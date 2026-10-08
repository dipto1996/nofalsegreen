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
  (1, 'PO-40415', 133, 20514),
  (2, 'PO-40412', 436, 20567),
  (3, 'PO-40402', 392, 20540),
  (4, 'PO-40416', 297, 20485);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES
  (5, 'PO-40413', 245, 20558),
  (6, 'PO-40403', 98, 20495),
  (7, 'PO-40409', 399, NULL),
  (8, 'PO-40406', 112, 20566);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES
  (9, 'PO-40411', 411, 20553),
  (10, 'PO-40414', 147, 20592),
  (11, 'PO-40405', 282, 20653),
  (12, 'PO-40408', 381, 20514);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES
  (13, 'PO-40408', 381, 20522),
  (14, 'PO-40404', 297, 20658),
  (15, 'PO-40410', NULL, 20654);
COMMIT;
