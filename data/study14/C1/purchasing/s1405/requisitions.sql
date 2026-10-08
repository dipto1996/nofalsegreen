-- Purchase request queue
-- source dataset: requisitions; 16 record(s); one VALUES tuple per record, in row_seq order
-- conventions:
--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)
--   *_cents US money in cents (100 = $1.00)
--   *_dan   force in decanewtons (100 daN = 1 kN)
--   *_ct    unit counts
--   NULL    = not recorded (never zero)
--   the same reference may occur in several tuples; each tuple is a separate record
BEGIN;
CREATE TABLE purchase_request (
    row_seq INTEGER PRIMARY KEY,  -- position in the extract
    ord_code TEXT NOT NULL,  -- order reference
    ask_cents NUMERIC,  -- sum asked for, US cents
    eta_epd INTEGER,  -- anticipated arrival (epoch day)
    req_state_cd TEXT  -- state of the purchase request
);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES
  (1, 'PO-40516', 17350000, 20555, 'Approved'),
  (2, 'PO-40507', 6450000, 20567, 'Approved'),
  (3, 'PO-40508', 12850000, 20486, 'Approved'),
  (4, 'PO-40503', 6900000, 20546, 'Approved'),
  (5, 'PO-40506', 8350000, 20551, 'Approved'),
  (6, 'PO-40514', 1900000, 20516, 'Approved'),
  (7, 'PO-40513', 6950000, 20461, 'Approved'),
  (8, 'PO-40515', 14200000, 20515, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES
  (9, 'PO-40512', 350000, 20587, 'Approved'),
  (10, 'PO-40505', 19200000, 20641, 'Approved'),
  (11, 'PO-40509', 6400000, 20559, 'Approved'),
  (12, 'PO-40510', 2550000, 20620, 'Approved'),
  (13, 'PO-40511', 15300000, 20472, 'Approved'),
  (14, 'PO-40501', 5700000, 20628, 'Approved'),
  (15, 'PO-40502', 4050000, 20632, 'Approved'),
  (16, 'PO-40504', 17800000, 20513, 'Approved');
COMMIT;
