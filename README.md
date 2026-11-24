# Student Lifecycle Analytics Platform

A data pipeline and analytics dashboard for tracking the student lifecycle from marketing lead acquisition to graduation outcomes.

The platform ingests raw inquiries, student enrollments, session attendance records, and weekly feedback surveys, loads them into a PostgreSQL star schema warehouse, and serves the metrics through SQL analytical queries and an interactive Streamlit application.

---

## Architecture & Data Flow

```
Raw CSV Files (data/raw/)
  ├── raw_leads.csv
  ├── raw_students.csv
  ├── raw_attendance.csv
  └── raw_feedback.csv
           │
           ▼
Python ETL Pipeline (etl/etl_pipeline.py)
  • Normalizes channel casing and whitespace
  • Cleans postal code formatting and nulls
  • Deduplicates primary keys
           │
           ▼
PostgreSQL Staging Layer
  ├── stg_leads
  ├── stg_students
  ├── stg_attendance
  └── stg_feedback
           │
           ▼
Warehouse Transformation (sql/02_load_dw.sql)
  • Idempotent upserts (ON CONFLICT)
  • Resolves dimension keys and referential integrity
           │
           ▼
Star Schema Data Warehouse
  • Dimensions: dim_courses, dim_marketing_sources, dim_students
  • Facts: fact_enrollments, fact_attendance, fact_feedback
           │
     ┌─────┴───────────────────────┐
     ▼                             ▼
SQL Analytics Queries        Streamlit Dashboard
(sql/03_analytics_queries.sql) (app/app.py)
```

---

## Project Structure

```text
Student-Lifecycle-Analytics-Platform/
├── .env.example                  # Database configuration template
├── .gitignore                    # Excludes secrets, venvs, and temp files
├── README.md                     # Documentation
├── requirements.txt              # Python dependencies
│
├── data/
│   └── raw/                      # Raw source CSV files
│       ├── raw_leads.csv
│       ├── raw_students.csv
│       ├── raw_attendance.csv
│       └── raw_feedback.csv
│
├── sql/
│   ├── 01_schema_setup.sql       # DDL for staging and star schema tables
│   ├── 02_load_dw.sql            # Warehouse loading and upsert logic
│   └── 03_analytics_queries.sql  # SQL queries for KPIs and cohort analysis
│
├── etl/
│   └── etl_pipeline.py           # Python extraction, staging, and DW load script
│
├── app/
│   ├── app.py                    # Streamlit analytics dashboard
│   ├── styles.css                # Custom dashboard styling
│   └── README.md                 # Dashboard notes and execution instructions
│
└── dashboards/
    ├── README.md                 # Power BI data modeling guide
    ├── powerbi_dax_measures.dax  # DAX measure definitions
    └── dashboard_specifications.md# Visual specifications and layout designs
```

---

## Data Model

The data warehouse uses a star schema structure:

- **dim_courses**: Courses offered (`course_id`, `course_name`).
- **dim_marketing_sources**: Marketing channels (`source_id`, `channel_name`).
- **dim_students**: Enrolled student profiles (`student_id`, `lead_id`, `course_id`, `enrollment_date`, `capstone_score`, `mock_grade`, `tech_stack`).
- **fact_enrollments**: Inquiries, marketing cost, and conversion outcomes (`enrollment_id`, `lead_id`, `channel_id`, `course_id`, `postal_code`, `inquiry_date`, `ad_cost`, `is_converted`).
- **fact_attendance**: Per-session student attendance status (`attendance_id`, `student_id`, `session_number`, `session_date`, `status`).
- **fact_feedback**: Weekly curriculum rating and comments (`feedback_id`, `student_id`, `week_number`, `rating`, `comments`).

---

## Local Setup

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 14+

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/<your-username>/Student-Lifecycle-Analytics-Platform.git
cd Student-Lifecycle-Analytics-Platform

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

Configure your PostgreSQL connection settings inside `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=student_lifecycle_db
DB_USER=postgres
DB_PASS=your_password
```

Create the target database in PostgreSQL if it does not already exist:
```sql
CREATE DATABASE student_lifecycle_db;
```

---

## Running the Project

### 1. Run the ETL Pipeline
To initialize the database tables, clean the raw CSV files, populate staging tables, and load the star schema warehouse:
```bash
python etl/etl_pipeline.py --full
```

To run subsequent incremental or refreshed loads without dropping existing tables:
```bash
python etl/etl_pipeline.py
```

### 2. Run Analytics Queries
Run the analytical queries against PostgreSQL using `psql`, pgAdmin, or DBeaver:
```bash
psql -U postgres -d student_lifecycle_db -f sql/03_analytics_queries.sql
```

### 3. Launch the Dashboard
Start the Streamlit dashboard:
```bash
python -m streamlit run app/app.py
```
Open your browser at `http://localhost:8501`.

---

## Key Findings

- **Marketing Attribution:** Walk-in leads convert at 18.4% with $0 ad spend. YouTube and Instagram convert at ~18% with customer acquisition costs (CAC) around $1,650 per enrolled student.
- **Geographic Dead Zones:** Inquiries from postal codes `641035` and `641045` yielded 0 conversions across all campaigns, indicating ad budget that can be redirected.
- **Attendance Progression:** Overall attendance begins at 84% in Session 1 and drops toward 78% by Session 12 as coursework difficulty increases.
- **Retention Correlation:** Students maintaining 90%+ attendance averaged a 77.65 capstone score, outperforming cohorts with lower attendance rates.
- **Curriculum Feedback:** Weekly feedback scores average 3.5 out of 5. Lower ratings (3 and below) commonly cite difficulty with SQL window functions and Power BI DAX formulas, highlighting topics that benefit from extra lab time.
