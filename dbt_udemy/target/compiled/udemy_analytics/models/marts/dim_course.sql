WITH source_ranked AS (
    SELECT *,
           -- [FIX] Khử mã trùng: Ưu tiên bản ghi có thông tin đầy đủ nhất
           ROW_NUMBER() OVER (
               PARTITION BY course_id 
               ORDER BY 
                    (CASE WHEN num_students > 0 THEN 1 ELSE 0 END) DESC,
                    scraped_at DESC
           ) as rn
    FROM "udemy_dw"."public_staging"."stg_courses"
),

stg AS (
    SELECT * FROM source_ranked WHERE rn = 1
)

SELECT
    stg.course_id,
    stg.title,
    stg.headline,
    stg.course_url,
    stg.published_date,
    stg.duration_hours,
    
    stg.list_price,
    
    -- Foreign Keys
    cat.category_id,
    lang.language_id,
    lvl.level_id

FROM stg
LEFT JOIN "udemy_dw"."public_marts"."dim_category" cat ON stg.category = cat.category_name
LEFT JOIN "udemy_dw"."public_marts"."dim_language" lang ON stg.language = lang.language_name
LEFT JOIN "udemy_dw"."public_marts"."dim_level" lvl ON stg.level = lvl.level_name