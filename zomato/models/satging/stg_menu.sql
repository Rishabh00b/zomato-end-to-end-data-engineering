select 
menu_id, 
try_to_number(r_id) as restaurant_id, 
f_id, 
cuisine, 
try_to_decimal(price,10,2) as price
from {{ source('raw', 'menu') }} where try_to_number(r_id) is not null and try_to_decimal(price,10,2) > 0