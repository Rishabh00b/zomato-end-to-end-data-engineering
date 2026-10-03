with spine as (
    select dateadd(day, seq4(), '2024-01-01'::date) as date_day 
    from 
    table(generator(rowcount=>1200)))
select date_day, year(date_day) as year, month(date_day) as month, monthname(date_day) as month_name,
       dayname(date_day) as day_name, (dayofweekiso(date_day)>=6) as is_weekend
from spine where date_day <= '2026-12-31'