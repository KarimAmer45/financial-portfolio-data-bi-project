-- Date dimension. The source is a fiscal-year-end snapshot, so this holds a
-- single reporting period until more periods are loaded.

select
    20240930 as date_key,
    cast('2024-09-30' as date) as reporting_period,
    2024 as year,
    'Q4' as quarter,
    9 as month,
    'FY2024 Year End' as period_label
