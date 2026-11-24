-- Data warehouse population script (idempotent upsert logic)

BEGIN;

-- dim_courses
INSERT INTO dim_courses (course_name)
SELECT DISTINCT TRIM(course_name) AS course_name
FROM (
    SELECT interested_course AS course_name FROM stg_leads WHERE interested_course IS NOT NULL AND TRIM(interested_course) <> ''
    UNION
    SELECT course_name FROM stg_students WHERE course_name IS NOT NULL AND TRIM(course_name) <> ''
) all_courses
ON CONFLICT (course_name) DO NOTHING;

-- dim_marketing_sources
INSERT INTO dim_marketing_sources (channel_name)
SELECT DISTINCT TRIM(channel) AS channel_name
FROM stg_leads
WHERE channel IS NOT NULL AND TRIM(channel) <> ''
ON CONFLICT (channel_name) DO NOTHING;

-- dim_students
INSERT INTO dim_students (
    student_id,
    lead_id,
    course_id,
    enrollment_date,
    capstone_score,
    mock_grade,
    tech_stack
)
SELECT 
    s.student_id,
    s.lead_id,
    c.course_id,
    s.enrollment_date,
    s.capstone_score,
    s.mock_grade,
    s.tech_stack
FROM stg_students s
LEFT JOIN dim_courses c 
    ON TRIM(LOWER(s.course_name)) = TRIM(LOWER(c.course_name))
ON CONFLICT (student_id) DO UPDATE SET
    lead_id         = EXCLUDED.lead_id,
    course_id       = EXCLUDED.course_id,
    enrollment_date = EXCLUDED.enrollment_date,
    capstone_score  = EXCLUDED.capstone_score,
    mock_grade      = EXCLUDED.mock_grade,
    tech_stack      = EXCLUDED.tech_stack;

-- fact_enrollments
INSERT INTO fact_enrollments (
    lead_id,
    channel_id,
    course_id,
    postal_code,
    inquiry_date,
    ad_cost,
    is_converted
)
SELECT 
    l.lead_id,
    m.source_id AS channel_id,
    c.course_id,
    COALESCE(NULLIF(TRIM(l.postal_code), ''), 'Unknown') AS postal_code,
    l.inquiry_date,
    COALESCE(l.ad_cost, 0.0),
    COALESCE(l.is_converted, 0)
FROM stg_leads l
LEFT JOIN dim_marketing_sources m 
    ON TRIM(LOWER(l.channel)) = TRIM(LOWER(m.channel_name))
LEFT JOIN dim_courses c 
    ON TRIM(LOWER(l.interested_course)) = TRIM(LOWER(c.course_name))
ON CONFLICT (lead_id) DO UPDATE SET
    channel_id   = EXCLUDED.channel_id,
    course_id    = EXCLUDED.course_id,
    postal_code  = EXCLUDED.postal_code,
    inquiry_date = EXCLUDED.inquiry_date,
    ad_cost      = EXCLUDED.ad_cost,
    is_converted = EXCLUDED.is_converted;

-- fact_attendance
INSERT INTO fact_attendance (
    student_id,
    session_number,
    session_date,
    status
)
SELECT 
    a.student_id,
    a.session_number,
    a.session_date,
    a.status
FROM stg_attendance a
INNER JOIN dim_students s 
    ON a.student_id = s.student_id
ON CONFLICT (student_id, session_number) DO UPDATE SET
    session_date = EXCLUDED.session_date,
    status       = EXCLUDED.status;

-- fact_feedback
INSERT INTO fact_feedback (
    feedback_id,
    student_id,
    week_number,
    rating,
    comments
)
SELECT 
    f.feedback_id,
    f.student_id,
    f.week_number,
    f.rating,
    f.comments
FROM stg_feedback f
INNER JOIN dim_students s 
    ON f.student_id = s.student_id
ON CONFLICT (feedback_id) DO UPDATE SET
    student_id  = EXCLUDED.student_id,
    week_number = EXCLUDED.week_number,
    rating      = EXCLUDED.rating,
    comments    = EXCLUDED.comments;

COMMIT;
