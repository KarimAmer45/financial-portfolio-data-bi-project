# DAX Measures

```DAX
Total Approved Dollars =
SUM(FactLendingActivity[approved_dollars])
```

```DAX
Total Loan Count =
SUM(FactLendingActivity[approved_loan_count])
```

```DAX
Average Loan Size =
DIVIDE(
    [Total Approved Dollars],
    [Total Loan Count]
)
```

```DAX
Total Guaranty Dollars =
SUM(FactLendingActivity[guaranty_dollars])
```

```DAX
Guaranty Rate =
DIVIDE(
    [Total Guaranty Dollars],
    [Total Approved Dollars]
)
```

```DAX
Lender Share =
DIVIDE(
    [Total Approved Dollars],
    CALCULATE(
        [Total Approved Dollars],
        ALL(DimLender)
    )
)
```

```DAX
Active Lenders =
DISTINCTCOUNT(DimLender[lender_key])
```

```DAX
Top 10 Lender Dollars =
SUMX(
    TOPN(
        10,
        ALL(DimLender[lender_name]),
        [Total Approved Dollars],
        DESC
    ),
    [Total Approved Dollars]
)
```

```DAX
Top 10 Lender Share =
DIVIDE(
    [Top 10 Lender Dollars],
    CALCULATE(
        [Total Approved Dollars],
        ALL(DimLender)
    )
)
```

```DAX
Failed Data Quality Checks =
COUNTROWS(
    FILTER(
        DataQualityReport,
        DataQualityReport[status] <> "pass"
    )
)
```

```DAX
Rejected Record Count =
COUNTROWS(RejectedRecords)
```
