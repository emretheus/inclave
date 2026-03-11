# Phase 1 - Step 8 Test Results

## Summary
- Date: 2026-03-11
- Tester: Mavi
- Model: qwen2.5-coder:7b
- Target: 7/10 pass rate

## Results

| # | CSV | Prompt | Pass? | Score | Notes |
|---|-----|--------|-------|-------|-------|
| 1 | sales_data.csv | Show the first 5 rows | ✅ | 9/10 | Clean code, correct output |
| 2 | sales_data.csv | Fill null discount values with 0 | ✅ | 7/10 | Core task correct, hardcoded path, overkill chunking |
| 3 | sales_data.csv | Convert date column to datetime | ⏳ | - | - |
| 4 | sales_data.csv | Group by city and show total revenue | ⏳ | - | - |
| 5 | weather.csv | Plot monthly temperature trend | ⏳ | - | - |
| 6 | sales_data.csv | Merge by customer_id | ⏳ | - | - |
| 7 | weather.csv | Find outliers using IQR method | ⏳ | - | - |
| 8 | sales_data.csv | Export to Excel with sheet name Sales | ⏳ | - | - |
| 9 | employees.csv | Create correlation matrix and heatmap | ⏳ | - | - |
| 10 | sales_data.csv | Find and remove duplicate rows | ⏳ | - | - |

## Final Score
- Runs successfully: ___ / 10
- Correct output: ___ / 10
- Success rate: ___%

## Observations
- 
- 

## Improvements Needed
-