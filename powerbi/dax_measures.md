# DAX Measures

All measures below are already defined on `fact_lending_activity` in the
semantic model. This file is the readable reference.

Base measures:

```DAX
Total Approved Dollars = SUM(fact_lending_activity[approved_dollars])

Total Loan Count = SUM(fact_lending_activity[approved_loan_count])

Total Guaranty Dollars = SUM(fact_lending_activity[guaranty_dollars])

Active Lenders = DISTINCTCOUNT(dim_lender[lender_key])
```

Ratios built on the base measures:

```DAX
Average Loan Size =
DIVIDE(
    [Total Approved Dollars],
    [Total Loan Count]
)

Guaranty Rate =
DIVIDE(
    [Total Guaranty Dollars],
    [Total Approved Dollars]
)
```

Share measures. `ALL(dim_lender)` removes the lender filter so the
denominator is always the grand total:

```DAX
Lender Share =
DIVIDE(
    [Total Approved Dollars],
    CALCULATE(
        [Total Approved Dollars],
        ALL(dim_lender)
    )
)

Top 10 Lender Dollars =
SUMX(
    TOPN(
        10,
        ALL(dim_lender[lender_name]),
        [Total Approved Dollars],
        DESC
    ),
    [Total Approved Dollars]
)

Top 10 Lender Share =
DIVIDE(
    [Top 10 Lender Dollars],
    CALCULATE(
        [Total Approved Dollars],
        ALL(dim_lender)
    )
)
```

Data-quality page measures:

```DAX
Failed Data Quality Checks =
COUNTROWS(
    FILTER(
        data_quality_report,
        data_quality_report[status] <> "pass"
    )
)

Rejected Record Count = COUNTROWS(rejected_records)
```
