# Expert labelling: instructions

Thank you for helping. You will label 80 compliance questions about synthetic
employers (no real person or company). Each takes 1-3 minutes; the whole set
should take about two to three hours. Please work alone and do not discuss
items with anyone else labelling the same set.

## What each row asks

Each row of `labelling_form.csv` is one obligation applied to one worker, LCA,
or employer, as of the evaluation date in the row. Open the CSV exports named
in the `exports` column (in `exports/`) and decide, from those records alone:

- **pass**: the records contain the information needed and show the obligation
  is met as of the evaluation date.
- **fail**: the records contain the information needed and show a violation as
  of the evaluation date.
- **needs_evidence**: the records do not contain firm-specific information
  needed to decide (a required item is missing or blank for this entity).
  Choose this whenever you would have to ask the client for something.
- **unmonitored**: the obligation cannot apply to this entity.

Use your professional knowledge of the rules, deadlines and thresholds. Do not
assume any fact about the employer that the records do not show.

## What to fill in

- `verdict`: one of the four words above.
- `confidence`: high, medium, or low.
- `comment` (optional but valuable): what decided it, or what is ambiguous.

The "information needed" column is the benchmark's own description of what an
assessment requires. If you disagree with it as a matter of law, decide as you
think correct and say so in the comment; that disagreement is itself useful.

## Returning

Save the CSV and send it back. You will be acknowledged by name in the paper
unless you prefer not to be.
