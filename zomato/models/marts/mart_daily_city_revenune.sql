select 
order_date, 
city, 
count(*) as orders, 
count_if(is_delivered) as delivered_orders,
round(div0(count_if(order_status='Cancelled'), count(*)),4) as cancel_rate,
sum(iff(is_delivered, sales_amount, 0)) as gmv,
round(div0(sum(iff(is_delivered, sales_amount,0)), count_if(is_delivered)),2) as aov
from {{ ref('fct_orders') }} group by 1,2