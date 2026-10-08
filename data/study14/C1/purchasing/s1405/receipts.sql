-- Goods-in notes
-- source dataset: receipts; 14 record(s); one VALUES tuple per record, in row_seq order
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
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (1, 'PO-40509', 41, 20566);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (2, 'PO-40514', 397, 20519);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (3, 'PO-40508', 378, 20493);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (4, 'PO-40505', 235, 20647);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (5, 'PO-40502', 281, 20638);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (6, 'PO-40512', 402, 20592);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (7, 'PO-40513', 451, 20464);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (8, 'PO-40504', 325, 20517);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (9, 'PO-40510', 128, 20630);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (10, 'PO-40504', 325, 20527);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (11, 'PO-40511', 139, NULL);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (12, 'PO-40501', 450, 20631);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (13, 'PO-40503', 423, 20550);
INSERT INTO goods_in_note (row_seq, ord_code, dock_unit_ct, goods_in_epd) VALUES (14, 'PO-40516', 306, 20557);
COMMIT;
