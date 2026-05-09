
WITH source AS (
    SELECT * FROM "udemy_dw"."raw"."courses"
),

ranked AS (
    SELECT
        course_id,
        TRIM(title) AS title,
        TRIM(headline) AS headline,
        language,
        level,
        -- [FIX] Ép kiểu TEXT->NUMERIC trước khi chia
        ROUND((course_duration_seconds::NUMERIC / 3600.0), 1) AS duration_hours,
        TO_DATE(NULLIF(TRIM(publishes_date), ''), 'DD/MM/YYYY') AS published_date,
        TO_DATE(NULLIF(TRIM(lasted_updated_date), ''), 'DD/MM/YYYY') AS last_updated_date,
        COALESCE(original_price::NUMERIC, 0) AS list_price,
        COALESCE(discount_price::NUMERIC, original_price::NUMERIC, 0) AS sale_price,
        COALESCE(num_students::NUMERIC, 0) AS num_students,
        COALESCE(num_reviews::NUMERIC, 0) AS num_reviews,
        -- [FIX] Ép kiểu TEXT->NUMERIC trước khi ROUND
        ROUND(avg_rating_score::NUMERIC, 1) AS rating,
        rating_distribution,
        _url AS course_url,
        _category AS category,
        TO_TIMESTAMP(_scraped_datetime, 'DD/MM/YYYY HH24:MI') AS scraped_at,
        
        -- [FIX] Tạo cột số thứ tự để thay thế QUALIFY
        ROW_NUMBER() OVER (
            PARTITION BY course_id, _scraped_datetime 
            ORDER BY _scraped_datetime DESC
        ) as rn
    FROM source
),

cleaned AS (
    -- [FIX] Lọc lấy dòng đầu tiên
    SELECT * FROM ranked WHERE rn = 1
),

ratings AS (
    SELECT
        -- Liệt kê các cột cần lấy (bỏ cột rn đi)
        course_id, title, headline, language, level, duration_hours,
        published_date, last_updated_date, list_price, sale_price,
        num_students, num_reviews, rating, course_url, category, scraped_at,
        rating_distribution,

        -- Parse JSON (Cú pháp này của Postgres OK)
        CAST(NULLIF(rating_distribution, 'None')::json->0->>'count' AS INT) AS rating_1,
        CAST(NULLIF(rating_distribution, 'None')::json->1->>'count' AS INT) AS rating_2,
        CAST(NULLIF(rating_distribution, 'None')::json->2->>'count' AS INT) AS rating_3,
        CAST(NULLIF(rating_distribution, 'None')::json->3->>'count' AS INT) AS rating_4,
        CAST(NULLIF(rating_distribution, 'None')::json->4->>'count' AS INT) AS rating_5
    FROM cleaned
)

SELECT * FROM ratings