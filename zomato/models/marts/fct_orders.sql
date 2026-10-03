{{ config(materialized='incremental', unique_key='order_id', incremental_strategy='merge', on_schema_change='append_new_columns') }}
select order_id, order_timestamp, order_date, customer_id, restaurant_id, city, cuisine,
       payment_method, order_status, is_delivered, items_count, sales_qty, subtotal, discount,
       delivery_fee, gst, sales_amount, customer_rating, delivery_time_min
from {{ ref('stg_orders') }}
{% if is_incremental() %}
  where order_timestamp > (select coalesce(max(order_timestamp),'1900-01-01'::timestamp) from {{ this }})
{% endif %}