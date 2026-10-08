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
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (1, 'PO-41001', 7200000, 20635, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (2, 'PO-41014', 850000, 20510, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (3, 'PO-41007', 13050000, 20585, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (4, 'PO-41011', 15550000, 20521, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (5, 'PO-41006', 19250000, 20575, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (6, 'PO-41016', 5550000, 20509, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (7, 'PO-41008', 1000000, 20569, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (8, 'PO-41015', 19050000, 20538, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (9, 'PO-41005', 13350000, 20486, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (10, 'PO-41003', 5350000, 20584, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (11, 'PO-41010', 18100000, 20510, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (12, 'PO-41002', 14900000, 20578, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (13, 'PO-41012', 13800000, 20576, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (14, 'PO-41004', 12400000, 20464, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (15, 'PO-41013', 2000000, 20482, 'Approved');
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, eta_epd, req_state_cd) VALUES (16, 'PO-41009', 1500000, 20552, 'Approved');
COMMIT;
