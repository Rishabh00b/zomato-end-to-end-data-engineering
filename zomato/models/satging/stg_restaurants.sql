-- parse the messy dimension (-- →null, 50+ ratings→50, ₹ 200→200, city after last comma):

select 
    id::number as restaurant_id, 
    name as restaurant_name,
    trim(coalesce(regexp_substr(city, '[^,]+$'), city)) as city,
    try_to_decimal(nullif(rating, '--'), 3, 1) as rating,
    try_to_number(regexp_substr(rating_count, '[0-9]+')) as rating_count,
    try_to_number(regexp_substr(cost, '[0-9]+')) as cost_for_two,
    cuisine, 
    lic_no as license_no
from {{ source('raw', 'restaurants') }} where try_to_number(id) is not null