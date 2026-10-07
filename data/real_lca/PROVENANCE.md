# Real LCA sample: provenance

- **Source file.** U.S. Department of Labor, Office of Foreign Labor Certification, *LCA Program Disclosure Data, FY2026 Q3*. URL: <https://www.dol.gov//media/LCA_Disclosure_Data_FY2026_Q3.xlsx>.
  - Retrieved 2026-10-06 from the OFLC Performance Data page.
  - 251,850,891 bytes; 1,032,736 sheet rows.
  - The Q2 release, which this sample was originally planned from, had been replaced by Q3. Q3 is cumulative and covers determinations from 2025-10-01 to 2026-06-30.
- **Why it was read in a browser.** The site refuses scripted downloads, so the workbook was read in a browser session. The steps below ran there; only their output left the browser.
- **Selection, applied mechanically before anything else.**
  1. Keep sheet row *r* iff `(r * 2654435761 mod 2^32) mod 300 == 0`. This kept 3,443 rows.
  2. Keep certified H-1B cases with annual wage and prevailing-wage units and both wages present. This left 1,238 rows.
  3. Order those by the FNV-1a hash of `CASE_NUMBER + "|20261006"` and take the first 120.
- **Columns kept.** Case number, job title, SOC code and title, full-time flag, begin and end dates (Excel serial numbers), wage range, prevailing wage and level, and worksite city and state.
  - Employer names, FEINs and contact or attorney names were never extracted.
- **Reproduction.** `extract_in_browser.js`, run in a browser on the OFLC page, repeats the selection and prints the counts above and the SHA-256 below. The disclosure workbook itself is not redistributed here.
- **Integrity.** SHA-256 of `sample_120.csv`, computed in the browser and reproduced locally: `1fffd6b8355d83e527e9201317d96fd58504000abbdffc4b66a875138ced69a3`.
