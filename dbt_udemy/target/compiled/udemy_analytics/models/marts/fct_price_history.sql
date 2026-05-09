WITH source AS (
    SELECT * FROM "udemy_dw"."public_staging"."stg_price_tracker"
)

SELECT
    -- Tạo ID duy nhất
    MD5(CAST(course_id AS TEXT) || '-' || CAST(scraped_at AS TEXT)) AS history_id,
    
    course_id,
    -- [MỚI] Thêm Title và URL từ chính bảng Tracker (Luôn có dữ liệu)
    title,
    course_url,
    
    list_price,
    sale_price,
    scraped_at AS recorded_at,
    
    -- Tính % giảm giá
    CASE 
        WHEN list_price > 0 THEN ROUND((1 - (sale_price / list_price))::NUMERIC * 100, 0)
        ELSE 0 
    END AS discount_percentage,
    
    -- Cờ báo đáy lịch sử (chỉ so sánh với các mức giá > 0 để tránh lỗi data)
    CASE 
        WHEN sale_price > 0 AND sale_price <= MIN(CASE WHEN sale_price > 0 THEN sale_price END) OVER (PARTITION BY course_id) THEN TRUE 
        ELSE FALSE 
    END AS is_lowest_price_ever

FROM source