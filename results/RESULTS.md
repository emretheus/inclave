# Phase 1 - Step 8 Test Results

## Scoring Rubric (out of 10)

| Criteria | Points |
|----------|--------|
| Core task completed correctly | 4 pts |
| Uses `csv_path` variable (not hardcoded) | 2 pts |
| Includes all necessary imports | 1 pt |
| Has error handling | 1 pt |
| Clean, readable code | 1 pt |
| No unnecessary/harmful extra code | 1 pt |

---

## Test Info
- Date: 2026-03-11
- Tester: Mavi
- Model: qwen2.5-coder:7b
- Target: 7/10 pass rate

## Results

| # | CSV | Prompt | Pass? | Score | Notes |
|---|-----|--------|-------|-------|-------|
| 1 | sales_data.csv | Show the first 5 rows | ✅ | 10/10 | Clean code, correct output |
| 2 | sales_data.csv | Fill null discount values with 0 | ✅ | 10/10 | Clean code, correct output |
| 3 | sales_data.csv | Convert date column to datetime |  ✅ | 10/10 | Clean code, correct output |
| 4 | sales_data.csv | Group by city and show total revenue |  ✅ | 10/10 | Clean code, correct output |
| 5 | weather.csv | Plot monthly temperature trend | ✅ | 10/10 | Clean code, correct output |
| 6 | sales_data.csv | Merge by customer_id | ✅ | 9/10 | Clean code, correct output, hardcoded second csv |
| 7 | weather.csv | Find outliers using IQR method | ✅ | 10/10 | Clean code, correct output |
| 8 | sales_data.csv | Export to Excel with sheet name Sales | ✅ | 9/10 | Clean code, correct output, hardcoded output file and unnecessary drop |
| 9 | employees.csv | Create correlation matrix and heatmap | ? | 8/10 | Clean code, never imported seaborn but used, error|
| 10 | sales_data.csv | Find and remove duplicate rows | ✅ | 9/10 | Clean code, correct output, hardcoded output file|

## Final Score
- Runs successfully: 9 / 10
- Correct output: 9 / 10
- Success rate: 90%

## Observations
- Model consistently wraps code in functions with csv_path as parameter ✅
- Model adds error handling (try/except) in every scenario ✅
- Model sometimes saves output to hardcoded filenames without being asked (Scenarios 3, 8, 10)
- Model used seaborn in Scenario 9 despite system prompt saying matplotlib only
- Model sometimes does extra operations (drop_duplicates, datetime conversion) without being asked
- CLI only supports single CSV input — multi-file merges require hardcoded second path (Scenario 6)
- Model uses chunking even for small files — overkill but not harmful
- Scenario 9 is the only failure — caused by missing seaborn import

## Improvements Needed
- Strengthen system prompt: "NEVER save output files unless explicitly asked"
- Strengthen system prompt: "Use ONLY pandas, numpy and matplotlib — do NOT use seaborn or any other library"
- Strengthen system prompt: "Always import every library you use at the top of the script"
- Add `--csv2` argument to CLI for multi-file merge operations
- --csv2 path passed to model but model still hardcodes it
- Phase 2: pass second CSV schema to pipeline just like primary CSV
- Add response validation in `_extract_code()` to detect missing imports
- Consider adding a syntax check before returning generated code to catch errors like Scenario 9
- Install seaborn as optional dependency since model naturally reaches for it in visualization tasks