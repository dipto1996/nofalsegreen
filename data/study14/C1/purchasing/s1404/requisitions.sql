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
    req_state_cd TEXT,  -- state of the purchase request
    eta_epd INTEGER  -- anticipated arrival (epoch day)
);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (1, 'PO-40402', 13600000, 'Approved', 20534);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (2, 'PO-40414', 5850000, 'Approved', 20590);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (3, 'PO-40415', 11250000, 'Approved', 20506);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (4, 'PO-40406', 14250000, 'Approved', 20562);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (5, 'PO-40416', 10150000, 'Approved', 20480);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (6, 'PO-40407', 16050000, 'Approved', 20470);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (7, 'PO-40411', 4200000, 'Approved', 20549);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (8, 'PO-40401', 3550000, 'Approved', 20585);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (9, 'PO-40409', 10500000, 'Approved', 20575);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (10, 'PO-40408', 2700000, 'Approved', 20514);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (11, 'PO-40413', 7950000, 'Approved', 20554);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (12, 'PO-40404', 3250000, 'Approved', 20653);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (13, 'PO-40410', 15650000, 'Approved', 20652);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (14, 'PO-40403', 10600000, 'Approved', 20486);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (15, 'PO-40412', 5850000, 'Approved', 20567);
INSERT INTO purchase_request (row_seq, ord_code, ask_cents, req_state_cd, eta_epd) VALUES (16, 'PO-40405', 10200000, 'Approved', 20652);
COMMIT;
