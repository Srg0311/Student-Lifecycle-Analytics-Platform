-- Analytics queries for Student Lifecycle Analytics Platform

-- 1. Marketing channel conversion rate and customer acquisition cost (CAC)
SELECT 
    m.channel_name,
    COUNT(e.lead_id) AS total_leads,
    SUM(e.is_converted) AS total_enrolled,
    ROUND((SUM(e.is_converted)::NUMERIC / NULLIF(COUNT(e.lead_id), 0)) * 100, 2) AS conversion_rate_pct,
    ROUND(SUM(e.ad_cost), 2) AS total_ad_spend,
    ROUND(SUM(e.ad_cost) / NULLIF(SUM(e.is_converted), 0), 2) AS customer_acquisition_cost_cac
FROM fact_enrollments e
LEFT JOIN dim_marketing_sources m ON e.channel_id = m.source_id
GROUP BY m.channel_name
ORDER BY conversion_rate_pct DESC;

-- 2. Inquiries and conversion rate by postal code (surfacing zero-conversion regions)
SELECT 
    e.postal_code,
    COUNT(e.lead_id) AS total_inquiries,
    SUM(e.is_converted) AS conversions,
    ROUND(SUM(e.ad_cost), 2) AS total_spend,
    ROUND((SUM(e.is_converted)::NUMERIC / NULLIF(COUNT(e.lead_id), 0)) * 100, 2) AS conversion_rate_pct,
    CASE 
        WHEN SUM(e.is_converted) = 0 THEN 'Zero Conversions'
        WHEN (SUM(e.is_converted)::NUMERIC / COUNT(e.lead_id)) >= 0.20 THEN 'Above Average'
        ELSE 'Average'
    END AS regional_status
FROM fact_enrollments e
GROUP BY e.postal_code
ORDER BY total_inquiries DESC;

-- 3. Course enrollment volume, average capstone score, and interview grade counts
SELECT 
    c.course_name,
    COUNT(DISTINCT s.student_id) AS total_students_enrolled,
    ROUND(AVG(s.capstone_score), 2) AS avg_capstone_score,
    MIN(s.capstone_score) AS min_capstone_score,
    MAX(s.capstone_score) AS max_capstone_score,
    COUNT(CASE WHEN s.mock_grade IN ('A+', 'A') THEN 1 END) AS high_grade_students,
    COUNT(CASE WHEN s.mock_grade = 'C' THEN 1 END) AS low_grade_students
FROM dim_students s
JOIN dim_courses c ON s.course_id = c.course_id
GROUP BY c.course_name
ORDER BY total_students_enrolled DESC;

-- 4. Students below the 75% attendance threshold
WITH student_attendance_summary AS (
    SELECT 
        s.student_id,
        s.lead_id,
        c.course_name,
        COUNT(a.session_number) AS total_sessions_scheduled,
        COUNT(CASE WHEN a.status = 'Present' THEN 1 END) AS sessions_attended,
        COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) AS sessions_missed,
        ROUND(
            (COUNT(CASE WHEN a.status = 'Present' THEN 1 END)::NUMERIC / NULLIF(COUNT(a.session_number), 0)) * 100,
            2
        ) AS attendance_rate_pct
    FROM dim_students s
    JOIN dim_courses c ON s.course_id = c.course_id
    LEFT JOIN fact_attendance a ON s.student_id = a.student_id
    GROUP BY s.student_id, s.lead_id, c.course_name
)
SELECT 
    student_id,
    course_name,
    total_sessions_scheduled,
    sessions_attended,
    sessions_missed,
    attendance_rate_pct,
    CASE 
        WHEN attendance_rate_pct < 70 THEN 'Critical'
        WHEN attendance_rate_pct < 80 THEN 'Warning'
        ELSE 'Normal'
    END AS attendance_tier
FROM student_attendance_summary
ORDER BY attendance_rate_pct ASC
LIMIT 20;

-- 5. Session-by-session attendance rate (progression across sessions 1 to 20)
SELECT 
    session_number,
    COUNT(student_id) AS total_logged,
    COUNT(CASE WHEN status = 'Present' THEN 1 END) AS present_count,
    COUNT(CASE WHEN status = 'Absent' THEN 1 END) AS absent_count,
    ROUND(
        (COUNT(CASE WHEN status = 'Present' THEN 1 END)::NUMERIC / NULLIF(COUNT(student_id), 0)) * 100,
        2
    ) AS session_attendance_rate_pct
FROM fact_attendance
GROUP BY session_number
ORDER BY session_number ASC;

-- 6. Weekly average feedback rating and response volume
SELECT 
    f.week_number,
    COUNT(f.feedback_id) AS total_feedbacks,
    ROUND(AVG(f.rating), 2) AS avg_weekly_rating,
    COUNT(CASE WHEN f.rating <= 2 THEN 1 END) AS dissatisfied_count,
    COUNT(CASE WHEN f.rating >= 4 THEN 1 END) AS satisfied_count
FROM fact_feedback f
GROUP BY f.week_number
ORDER BY f.week_number ASC;

-- 7. Average capstone exit score by attendance bracket
WITH attendance_calc AS (
    SELECT 
        student_id,
        ROUND(
            (COUNT(CASE WHEN status = 'Present' THEN 1 END)::NUMERIC / NULLIF(COUNT(session_number), 0)) * 100, 
            2
        ) AS attendance_pct
    FROM fact_attendance
    GROUP BY student_id
)
SELECT 
    CASE 
        WHEN att.attendance_pct >= 90 THEN '90-100% Attendance'
        WHEN att.attendance_pct >= 80 THEN '80-89% Attendance'
        WHEN att.attendance_pct >= 70 THEN '70-79% Attendance'
        ELSE '< 70% Attendance'
    END AS attendance_bracket,
    COUNT(s.student_id) AS student_count,
    ROUND(AVG(s.capstone_score), 2) AS avg_capstone_score,
    ROUND(MIN(s.capstone_score), 2) AS min_capstone_score,
    ROUND(MAX(s.capstone_score), 2) AS max_capstone_score
FROM dim_students s
JOIN attendance_calc att ON s.student_id = att.student_id
GROUP BY attendance_bracket
ORDER BY avg_capstone_score DESC;
