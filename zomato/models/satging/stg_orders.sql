select order_id, order_timestamp, order_date, user_id as customer_id, r_id as restaurant_id,
    trim(coalesce(regexp_substr(restaurant_city, '[^,]+$'), restaurant_city)) as city,
    cuisine, items_count, sales_qty, subtotal, discount, delivery_fee, gst, sales_amount,
    currency, payment_method, order_status, (order_status='Delivered') as is_delivered,
    customer_rating, delivery_time_min
from {{ source('raw', 'orders') }}