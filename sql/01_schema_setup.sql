-- Schema definition for Student Lifecycle Analytics Platform

DROP TABLE IF EXISTS fact_feedback CASCADE;
DROP TABLE IF EXISTS fact_attendance CASCADE;
DROP TABLE IF EXISTS fact_enrollments CASCADE;
DROP TABLE IF EXISTS dim_students CASCADE;
DROP TABLE IF EXISTS dim_courses CASCADE;
DROP TABLE IF EXISTS dim_marketing_sources CASCADE;

DROP TABLE IF EXISTS stg_feedback CASCADE;
DROP TABLE IF EXISTS stg_attendance CASCADE;
DROP TABLE IF EXISTS stg_students CASCADE;
DROP TABLE IF EXISTS stg_leads CASCADE;

-- Safely remove legacy staging objects if present
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN 
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name IN ('fact_enrollments_staging', 'dim_students_staging', 'fact_attendance_staging', 'raw_feedback_staging')
    LOOP
        IF rec.table_type = 'VIEW' THEN
            EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(rec.table_name) || ' CASCADE;';
        ELSE
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(rec.table_name) || ' CASCADE;';
        END IF;
    END LOOP;
END $$;

-- Staging tables
CREATE TABLE stg_leads (
    lead_id VARCHAR(50) PRIMARY KEY,
    channel VARCHAR(50),
    postal_code VARCHAR(20),
    interested_course VARCHAR(100),
    inquiry_date DATE,
    ad_cost NUMERIC(10, 2),
    is_converted INT
);

CREATE TABLE stg_students (
    student_id VARCHAR(50) PRIMARY KEY,
    lead_id VARCHAR(50),
    course_name VARCHAR(100),
    enrollment_date DATE,
    capstone_score INT,
    mock_grade VARCHAR(10),
    tech_stack TEXT
);

CREATE TABLE stg_attendance (
    student_id VARCHAR(50),
    session_number INT,
    session_date DATE,
    status VARCHAR(20),
    PRIMARY KEY (student_id, session_number)
);

CREATE TABLE stg_feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    student_id VARCHAR(50),
    week_number INT,
    rating INT,
    comments TEXT
);

-- Backward compatibility views
CREATE OR REPLACE VIEW fact_enrollments_staging AS SELECT * FROM stg_leads;
CREATE OR REPLACE VIEW dim_students_staging AS SELECT * FROM stg_students;
CREATE OR REPLACE VIEW fact_attendance_staging AS SELECT * FROM stg_attendance;
CREATE OR REPLACE VIEW raw_feedback_staging AS SELECT * FROM stg_feedback;

-- Star schema dimensions
CREATE TABLE dim_courses (
    course_id SERIAL PRIMARY KEY,
    course_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE dim_marketing_sources (
    source_id SERIAL PRIMARY KEY,
    channel_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE dim_students (
    student_id VARCHAR(50) PRIMARY KEY,
    lead_id VARCHAR(50),
    course_id INT REFERENCES dim_courses(course_id) ON DELETE SET NULL,
    enrollment_date DATE,
    capstone_score INT,
    mock_grade VARCHAR(10),
    tech_stack TEXT
);

-- Star schema facts
CREATE TABLE fact_enrollments (
    enrollment_id SERIAL PRIMARY KEY,
    lead_id VARCHAR(50) UNIQUE NOT NULL,
    channel_id INT REFERENCES dim_marketing_sources(source_id) ON DELETE SET NULL,
    course_id INT REFERENCES dim_courses(course_id) ON DELETE SET NULL,
    postal_code VARCHAR(20),
    inquiry_date DATE,
    ad_cost NUMERIC(10, 2),
    is_converted INT
);

CREATE TABLE fact_attendance (
    attendance_id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) REFERENCES dim_students(student_id) ON DELETE CASCADE,
    session_number INT,
    session_date DATE,
    status VARCHAR(20),
    CONSTRAINT uq_student_session UNIQUE (student_id, session_number)
);

CREATE TABLE fact_feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    student_id VARCHAR(50) REFERENCES dim_students(student_id) ON DELETE CASCADE,
    week_number INT,
    rating INT,
    comments TEXT
);

CREATE INDEX idx_enrollments_channel ON fact_enrollments(channel_id);
CREATE INDEX idx_enrollments_course ON fact_enrollments(course_id);
CREATE INDEX idx_enrollments_inquiry_date ON fact_enrollments(inquiry_date);
CREATE INDEX idx_students_course ON dim_students(course_id);
CREATE INDEX idx_attendance_student ON fact_attendance(student_id);
CREATE INDEX idx_attendance_date ON fact_attendance(session_date);
CREATE INDEX idx_feedback_student ON fact_feedback(student_id);
CREATE INDEX idx_feedback_rating ON fact_feedback(rating);
