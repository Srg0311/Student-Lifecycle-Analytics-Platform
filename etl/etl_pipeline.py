import os
import sys
import argparse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "student_lifecycle_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "your_password")
DB_PORT = os.getenv("DB_PORT", "5432")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )


def clean_leads_data(filepath='data/raw/raw_leads.csv') -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing file: {filepath}")

    df = pd.read_csv(filepath)

    channel_norm = {
        'instagram': 'Instagram',
        'youtube': 'YouTube',
        'walk-in': 'Walk-in',
        'walk in': 'Walk-in'
    }
    df['channel'] = df['channel'].astype(str).str.strip()
    df['channel'] = df['channel'].apply(lambda x: channel_norm.get(x.lower(), x.title()))

    # Fill missing postal codes and remove float formatting artifacts (.0)
    df['postal_code'] = (
        df['postal_code']
        .fillna('Unknown')
        .astype(str)
        .str.replace(r'\.0$', '', regex=True)
        .str.strip()
    )
    df['postal_code'] = df['postal_code'].replace(['nan', 'None', ''], 'Unknown')
    df['interested_course'] = df['interested_course'].astype(str).str.strip()
    df['inquiry_date'] = pd.to_datetime(df['inquiry_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['ad_cost'] = pd.to_numeric(df['ad_cost'], errors='coerce').fillna(0.0).round(2)
    df['is_converted'] = pd.to_numeric(df['is_converted'], errors='coerce').fillna(0).astype(int)

    df = df.drop_duplicates(subset=['lead_id'], keep='first')
    return df[['lead_id', 'channel', 'postal_code', 'interested_course', 'inquiry_date', 'ad_cost', 'is_converted']]


def clean_students_data(filepath='data/raw/raw_students.csv') -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing file: {filepath}")

    df = pd.read_csv(filepath)

    df['student_id'] = df['student_id'].astype(str).str.strip()
    df['lead_id'] = df['lead_id'].astype(str).str.strip()
    df['course_name'] = df['course_name'].astype(str).str.strip()
    df['enrollment_date'] = pd.to_datetime(df['enrollment_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['capstone_score'] = pd.to_numeric(df['capstone_score'], errors='coerce').fillna(0).astype(int)
    df['mock_grade'] = df['mock_grade'].astype(str).str.strip().str.upper()
    df['tech_stack'] = df['tech_stack'].astype(str).str.strip()

    df = df.drop_duplicates(subset=['student_id'], keep='first')
    return df[['student_id', 'lead_id', 'course_name', 'enrollment_date', 'capstone_score', 'mock_grade', 'tech_stack']]


def clean_attendance_data(filepath='data/raw/raw_attendance.csv') -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing file: {filepath}")

    df = pd.read_csv(filepath)

    df['student_id'] = df['student_id'].astype(str).str.strip()
    df['session_number'] = pd.to_numeric(df['session_number'], errors='coerce').fillna(0).astype(int)
    df['session_date'] = pd.to_datetime(df['session_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['status'] = df['status'].astype(str).str.strip().str.capitalize()

    df = df.dropna(subset=['student_id', 'session_date', 'status'])
    df = df[df['student_id'] != '']
    df = df.drop_duplicates(subset=['student_id', 'session_number'], keep='first')
    return df[['student_id', 'session_number', 'session_date', 'status']]


def clean_feedback_data(filepath='data/raw/raw_feedback.csv') -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing file: {filepath}")

    df = pd.read_csv(filepath)

    df['feedback_id'] = df['feedback_id'].astype(str).str.strip()
    df['student_id'] = df['student_id'].astype(str).str.strip()
    df['week_number'] = pd.to_numeric(df['week_number'], errors='coerce').fillna(1).astype(int)
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(3).astype(int).clip(1, 5)
    df['comments'] = df['comments'].astype(str).str.strip()

    df = df.drop_duplicates(subset=['feedback_id'], keep='first')
    return df[['feedback_id', 'student_id', 'week_number', 'rating', 'comments']]


def execute_sql_file(conn, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    with conn.cursor() as cursor:
        cursor.execute(sql)
    conn.commit()


def stage_dataframe(cursor, conn, df: pd.DataFrame, table_name: str, truncate_first: bool = True):
    if truncate_first:
        cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;")

    cols = list(df.columns)
    cols_quoted = ', '.join([f'"{c}"' for c in cols])
    query = f"INSERT INTO {table_name} ({cols_quoted}) VALUES %s"

    tuples = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False)]
    execute_values(cursor, query, tuples, page_size=2000)
    conn.commit()


def run_etl(init_schema: bool = False, load_dw: bool = True):
    print("Extracting and transforming raw CSVs...")
    leads_df = clean_leads_data()
    students_df = clean_students_data()
    attendance_df = clean_attendance_data()
    feedback_df = clean_feedback_data()

    conn = get_db_connection()
    try:
        if init_schema:
            schema_file = os.path.join('sql', '01_schema_setup.sql')
            if os.path.exists(schema_file):
                print("Initializing schema...")
                execute_sql_file(conn, schema_file)

        print("Loading staging tables...")
        with conn.cursor() as cursor:
            stage_dataframe(cursor, conn, leads_df, 'stg_leads')
            stage_dataframe(cursor, conn, students_df, 'stg_students')
            stage_dataframe(cursor, conn, attendance_df, 'stg_attendance')
            stage_dataframe(cursor, conn, feedback_df, 'stg_feedback')

        if load_dw:
            dw_file = os.path.join('sql', '02_load_dw.sql')
            if os.path.exists(dw_file):
                print("Transforming and populating star schema...")
                execute_sql_file(conn, dw_file)

        print("Pipeline finished successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"Error during ETL execution: {exc}", file=sys.stderr)
        raise exc
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Student Lifecycle ETL Pipeline")
    parser.add_argument('--init-schema', action='store_true', help="Initialize database tables before loading")
    parser.add_argument('--no-dw', action='store_true', help="Skip warehouse transformation step")
    parser.add_argument('--full', action='store_true', help="Run schema init, staging load, and star schema load")

    args = parser.parse_args()
    run_etl(init_schema=(args.init_schema or args.full), load_dw=(not args.no_dw))
