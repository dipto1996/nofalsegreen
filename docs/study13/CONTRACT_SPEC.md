# Study 13 decision contracts (held-out)

Six decision rules, two per workflow. None appears in Studies 9–12. Each rule is a predicate
over **facts**. Each fact is established only by the document fields listed for it; every
other document and field, however it is named, does not establish it.

This specification is written for the canonical form of the records: one CSV file per
document, `<document>.csv`, with the canonical column names below. (The packets shown to
models render the same records in other layouts; the canonical form is the ground truth.)

## Documents (canonical columns)

The first column of every document is the entity key: `employee_id` (workforce), `po_id`
(purchasing), `part_id` (engineering). A document may hold zero, one or several rows for an
entity. A blank cell holds no value. Dates are ISO `YYYY-MM-DD`; amounts are decimal
numbers.

| Workflow | Document | Columns |
|---|---|---|
| workforce | `hr_roster` | employee_id, reverification_status, visa_end_date, notice_status, planned_filing_date |
| workforce | `work_authorizations` | employee_id, document_type, expires_on |
| workforce | `ead_cards` | employee_id, card_expiry |
| workforce | `reverifications` | employee_id, completed_on |
| workforce | `lca_notices` | employee_id, posted_on, removed_on |
| workforce | `lca_filings` | employee_id, filed_on |
| workforce | `dol_receipts` | employee_id, receipt_date |
| purchasing | `requisitions` | po_id, status, requested_amount, expected_delivery |
| purchasing | `purchase_orders` | po_id, po_amount |
| purchasing | `invoices` | po_id, invoice_amount, invoiced_qty, due_on |
| purchasing | `receipts` | po_id, received_qty, received_on |
| purchasing | `warehouse_scans` | po_id, scan_date |
| purchasing | `payments` | po_id, paid_on |
| engineering | `parts` | part_id, qa_status, target_load_kn, planned_test_date |
| engineering | `calibration_log` | part_id, calibrated_on |
| engineering | `test_reports` | part_id, tested_on, measured_load_kn |
| engineering | `lab_certificates` | part_id, test_date, certified_load_kn |
| engineering | `spec_sheets` | part_id, min_load_kn |

`hr_roster`, `requisitions` and `parts` establish no fact of any rule.

## Rules

| Rule | Predicate | Facts and their sources (in priority order) |
|---|---|---|
| `wf.reverify_window` | E − 90 days ≤ R ≤ E | E = authorization expiry: `work_authorizations.expires_on`, else `ead_cards.card_expiry`. R = reverification date: `reverifications.completed_on`. |
| `wf.notice_posting` | P ≤ F and Q ≥ P + 10 business days | P = notice posted: `lca_notices.posted_on`. Q = notice removed: `lca_notices.removed_on`. F = LCA filed: `lca_filings.filed_on`, else `dol_receipts.receipt_date`. |
| `pa.three_way_match` | I ≤ O and Rq ≥ Iq | I = invoice amount: `invoices.invoice_amount`. O = order amount: `purchase_orders.po_amount`. Rq = received quantity: `receipts.received_qty`. Iq = invoiced quantity: `invoices.invoiced_qty`. |
| `pa.paid_in_window` | V ≤ Y ≤ D | V = goods received: `receipts.received_on`, else `warehouse_scans.scan_date`. Y = paid: `payments.paid_on`. D = payment due: `invoices.due_on`. |
| `ea.calibration_current` | C ≤ T ≤ C + 365 days | C = calibrated: `calibration_log.calibrated_on`. T = tested: `test_reports.tested_on`, else `lab_certificates.test_date`. |
| `ea.load_with_margin` | M ≥ 1.2 × N | M = measured load: `lab_certificates.certified_load_kn`, else `test_reports.measured_load_kn`. N = specified minimum: `spec_sheets.min_load_kn`. |

"Days" are calendar days. **Business days** exclude Saturdays, Sundays and US federal
holidays, using observed dates (a holiday on a Saturday is observed the Friday before, one on
a Sunday the Monday after). "P + 10 business days" counts forward from P; P itself is day 0.

## Verdicts, for each (rule, entity)

Every entity that appears in any document of the workflow is evaluated for both rules of
that workflow.

1. **Gather each fact's value.** Take the fact's sources in priority order. The first source
   that holds at least one non-blank value for the entity decides the fact. If that source's
   non-blank values for the entity all agree, the fact has that value. If they disagree, the
   fact is **conflicting**, whatever the row order and whatever lower-priority sources say.
   If no source holds a value, the fact is **unknown**.
2. **Conflicting fact.** If any fact of the rule is conflicting, the verdict is
   `needs_evidence`.
3. **No unknown facts.** If every fact has a value, the verdict is `pass` if the predicate
   holds and `fail` otherwise.
4. **Some unknown facts.** Consider every possible value of the unknown facts (any date; any
   amount ≥ 0): `pass` if the predicate would hold for every possible value, `fail` if it
   would fail for every possible value, `needs_evidence` otherwise. For example, with I > O
   known, `pa.three_way_match` is `fail` whatever the quantities are.
