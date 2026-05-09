WITH source AS (
    SELECT * FROM "udemy_dw"."public_staging"."stg_courses"
),

ranked_source AS (
    SELECT *,
           -- [FIX] Ưu tiên bản ghi có dữ liệu (num_students > 0) sau đó mới đến thời gian
           ROW_NUMBER() OVER (
               PARTITION BY course_id 
               ORDER BY 
                    (CASE WHEN num_students > 0 THEN 1 ELSE 0 END) DESC,
                    scraped_at DESC
           ) as rn
    FROM source
),

latest_snapshot AS (
    SELECT 
        -- [FIX] Tự tạo ID bằng MD5
        MD5(CAST(course_id AS TEXT) || '-' || CAST(scraped_at AS TEXT)) AS snapshot_id,

        course_id,
        num_students,
        num_reviews,
        rating,
        rating_1, rating_2, rating_3, rating_4, rating_5,
        last_updated_date,
        scraped_at
        
    FROM ranked_source
    WHERE rn = 1
)

SELECT * FROM latest_snapshot