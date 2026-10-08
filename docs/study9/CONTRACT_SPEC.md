# Study 9 decision contracts: specification for an independent checker

A **packet** is a directory of CSV files, one per table. The table name is the file stem,
and the first row of each file is its header. Each row describes one entity, identified by
the key column named below. Some rows or cells may be missing. A table may contain two rows
for the same entity.

## Tables

| Workflow | Key | Tables (columns) |
|---|---|---|
| workforce | `employee_id` | `hr_roster` (employee_id, hire_date, onboarding_status, onboarding_completed_on, salary_of_record); `i9_records` (employee_id, first_day_of_employment, section2_completed_on); `payroll` (employee_id, annualised_gross); `lca` (employee_id, prevailing_wage); `actual_wage_system` (employee_id, actual_wage) |
| purchasing | `po_id` | `requisitions` (po_id, status, requested_amount, planned_approval_date); `purchase_orders` (po_id, po_amount, po_date); `signed_approvals` (po_id, approved_amount, signed_on); `erp_ledger` (po_id, order_date) |
| engineering | `part_id` | `qa_tracker` (part_id, qa_status, target_load_kn, planned_test_date); `test_reports` (part_id, measured_load_kn, tested_on); `spec_sheets` (part_id, min_load_kn); `shipping_log` (part_id, shipped_on) |

Dates are ISO `YYYY-MM-DD`. Amounts are numbers.

## Rules

Each rule applies to every entity that appears in any table of its workflow. Each fact is
established **only** by the listed `table.column`. Every other column is irrelevant, even one
whose name sounds relevant.

| Rule | Predicate | Facts and their only sources |
|---|---|---|
| `wf.section2` | S ≤ (F + 3 business days) | F = first day: `i9_records.first_day_of_employment`, else `hr_roster.hire_date`. If both are present and differ, the `i9_records` value prevails. S = `i9_records.section2_completed_on`. |
| `wf.required_wage` | P ≥ max(W, A) | P = `payroll.annualised_gross`; W = `lca.prevailing_wage`; A = `actual_wage_system.actual_wage` |
| `pa.within_approval` | O ≤ G | O = `purchase_orders.po_amount`; G = `signed_approvals.approved_amount` |
| `pa.approved_before_order` | D ≤ T | D = `signed_approvals.signed_on`; T = order date: `purchase_orders.po_date`, else `erp_ledger.order_date`. If both are present and differ, `purchase_orders` prevails. |
| `ea.load_meets_spec` | M ≥ N | M = `test_reports.measured_load_kn`; N = `spec_sheets.min_load_kn` |
| `ea.tested_before_ship` | X ≤ Y | X = `test_reports.tested_on`; Y = `shipping_log.shipped_on` |

**Business days** exclude Saturdays, Sundays and US federal holidays. Use the observed dates:
a holiday on a Saturday is observed the Friday before, and one on a Sunday the Monday after.
"F + 3 business days" counts forward from F; F itself is day 0.

## Verdicts, for each (rule, entity)

1. **Gather each fact's value.** For each fact, collect every non-empty value from its listed
   sources for that entity.
   - If two or more values disagree, apply the stated priority. Priority ranks sources, not
     rows: the highest-priority source holding a value decides, and if that source's own rows
     disagree, the fact is **conflicting**, whatever the row order.
   - If the fact has a single listed source and its values disagree (for example, two
     different rows), the fact is **conflicting**.
2. **Conflicting fact.** If any fact is conflicting, the verdict is `needs_evidence`.
3. **No unknown facts.** If every fact has a value, the verdict is `pass` if the predicate
   holds and `fail` otherwise.
4. **Some unknown facts.** If some facts have no value, consider every possible value of the
   unknown facts:
   - `pass` if the predicate would hold for every possible value;
   - `fail` if it would fail for every possible value;
   - `needs_evidence` otherwise.

   For example, with P known and below W while A is unknown, `wf.required_wage` is `fail`.

## Output

```bash
python3 labelcheck/contract_checker.py <workflow> <packet_dir>
```

Print JSON `{"<rule_id>::<entity_id>": "<verdict>"}` for every rule of the workflow and every
entity id found in any of the workflow's tables.
