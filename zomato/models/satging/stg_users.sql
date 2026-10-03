select 
    user_id::number as customer_id, 
    name as customer_name, 
    lower(email) as email,
    try_to_number(age) as age, 
    gender, 
    marital_status, 
    occupation,
    monthly_income as income_band, 
    education, 
    try_to_number(family_size) as family_size
from {{ source('raw', 'users') }} where try_to_number(user_id) is not null