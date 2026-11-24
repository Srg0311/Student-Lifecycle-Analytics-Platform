# BI Dashboards & Data Modeling

This folder contains specifications and DAX measures for connecting external BI tools (such as Power BI or Tableau) to the PostgreSQL star schema.

## PostgreSQL Connection
- Host: `localhost:5432`
- Database: `student_lifecycle_db`
- Recommended Mode: Import

## Star Schema Relationships
1. `dim_courses[course_id]` 1 ➔ * `fact_enrollments[course_id]`
2. `dim_courses[course_id]` 1 ➔ * `dim_students[course_id]`
3. `dim_marketing_sources[source_id]` 1 ➔ * `fact_enrollments[channel_id]`
4. `dim_students[student_id]` 1 ➔ * `fact_attendance[student_id]`
5. `dim_students[student_id]` 1 ➔ * `fact_feedback[student_id]`

## Files
- `powerbi_dax_measures.dax`: Formulas for Conversion Rate, CAC, Attendance %, and Capstone averages.
- `dashboard_specifications.md`: Page-by-page visual layout and KPI specifications.
