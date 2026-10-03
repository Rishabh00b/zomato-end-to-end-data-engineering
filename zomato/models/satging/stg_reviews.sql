select
r.review_id,
r.order_id,
r.user_id::number as customer_id,
r.restaurant_id::string as restaurant_id,
r.rating::number as rating,
r.comment::string as comment,
r.review_date::DATE as review_date,
res.city as city,
from {{ source('raw', 'reviews') }} r
left join {{ ref('stg_restaurants') }} res on r.restaurant_id = res.restaurant_id
where r.comment is not null