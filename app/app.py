import os
import sys
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import psycopg2
import streamlit as st
import altair as alt
from dotenv import load_dotenv

st.set_page_config(
    page_title="Student Lifecycle Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "student_lifecycle_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "your_password")
DB_PORT = os.getenv("DB_PORT", "5432")

# Load CSS
styles_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(styles_path):
    with open(styles_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_lifecycle_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=3
        )

        q_enroll = """
            SELECT 
                e.lead_id,
                COALESCE(m.channel_name, 'Unknown') AS channel,
                COALESCE(c.course_name, 'General') AS course,
                e.postal_code,
                e.inquiry_date,
                e.ad_cost,
                e.is_converted
            FROM fact_enrollments e
            LEFT JOIN dim_marketing_sources m ON e.channel_id = m.source_id
            LEFT JOIN dim_courses c ON e.course_id = c.course_id;
        """
        df_enroll = pd.read_sql(q_enroll, conn)

        q_students = """
            SELECT 
                s.student_id,
                s.lead_id,
                c.course_name AS course,
                s.enrollment_date,
                s.capstone_score,
                s.mock_grade,
                s.tech_stack
            FROM dim_students s
            LEFT JOIN dim_courses c ON s.course_id = c.course_id;
        """
        df_students = pd.read_sql(q_students, conn)

        q_attendance = """
            SELECT 
                a.student_id,
                a.session_number,
                a.session_date,
                a.status,
                c.course_name AS course
            FROM fact_attendance a
            LEFT JOIN dim_students s ON a.student_id = s.student_id
            LEFT JOIN dim_courses c ON s.course_id = c.course_id;
        """
        df_attendance = pd.read_sql(q_attendance, conn)

        q_feedback = """
            SELECT 
                f.feedback_id,
                f.student_id,
                f.week_number,
                f.rating,
                f.comments,
                c.course_name AS course
            FROM fact_feedback f
            LEFT JOIN dim_students s ON f.student_id = s.student_id
            LEFT JOIN dim_courses c ON s.course_id = c.course_id;
        """
        df_feedback = pd.read_sql(q_feedback, conn)
        conn.close()

        return df_enroll, df_students, df_attendance, df_feedback, "PostgreSQL • student_lifecycle_db"
    except Exception:
        # Fallback to local raw files if database is not reachable
        raw_leads = pd.read_csv('data/raw/raw_leads.csv')
        raw_students = pd.read_csv('data/raw/raw_students.csv')
        raw_attendance = pd.read_csv('data/raw/raw_attendance.csv')
        raw_feedback = pd.read_csv('data/raw/raw_feedback.csv')

        raw_leads['channel'] = raw_leads['channel'].astype(str).str.strip().str.title()
        raw_leads['postal_code'] = raw_leads['postal_code'].fillna('Unknown').astype(str).str.replace(r'\.0$', '', regex=True)
        raw_leads['course'] = raw_leads['interested_course']

        df_att = raw_attendance.merge(
            raw_students[['student_id', 'course_name']].rename(columns={'course_name': 'course'}),
            on='student_id',
            how='left'
        )

        df_fb = raw_feedback.merge(
            raw_students[['student_id', 'course_name']].rename(columns={'course_name': 'course'}),
            on='student_id',
            how='left'
        )

        raw_students = raw_students.rename(columns={'course_name': 'course'})
        return raw_leads, raw_students, df_att, df_fb, "Local CSV Mode (Offline)"


def render_kpi(label: str, value: str, pill_text: str, pill_type: str = "green"):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">{label}</div>
        <div class="kpi-body">
            <div class="kpi-value">{value}</div>
            <div class="kpi-subtext">
                <span class="kpi-pill pill-{pill_type}">{pill_text}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_chart_header(title: str, tag: str = "METRIC"):
    st.markdown(f"""
    <div class="chart-card-header">
        <span>{title}</span>
        <span class="tag">{tag}</span>
    </div>
    """, unsafe_allow_html=True)


def render_takeaway(text: str):
    st.markdown(f"""
    <div class="takeaway-card">
        <div class="takeaway-header">Key Takeaway</div>
        <p class="takeaway-text">{text}</p>
    </div>
    """, unsafe_allow_html=True)


df_enroll, df_students, df_attendance, df_feedback, db_badge_label = load_lifecycle_data()

# Sidebar
with st.sidebar:
    st.markdown("### DATABASE STATUS")
    st.markdown(f"""
    <div class="db-badge">
        <span class="db-dot"></span>
        <span>{db_badge_label}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### FILTERS")

    course_options = ["All Courses"] + sorted(list(df_enroll['course'].dropna().unique()))
    selected_course = st.selectbox("Course", course_options)

    channel_options = ["All Channels"] + sorted(list(df_enroll['channel'].dropna().unique()))
    selected_channel = st.selectbox("Channel", channel_options)

    st.markdown(f"""
    <div class="sidebar-pipeline-note">
        <strong>Pipeline Status</strong><br>
        Source: <code>data/raw/*.csv</code><br>
        Storage: PostgreSQL <code>student_lifecycle_db</code><br>
        Schema: Star Schema (idempotent upsert)
    </div>
    """, unsafe_allow_html=True)

# Filter application
filtered_enroll = df_enroll.copy()
filtered_students = df_students.copy()
filtered_attendance = df_attendance.copy()
filtered_feedback = df_feedback.copy()

if selected_course != "All Courses":
    filtered_enroll = filtered_enroll[filtered_enroll['course'] == selected_course]
    filtered_students = filtered_students[filtered_students['course'] == selected_course]
    filtered_attendance = filtered_attendance[filtered_attendance['course'] == selected_course]
    filtered_feedback = filtered_feedback[filtered_feedback['course'] == selected_course]

if selected_channel != "All Channels":
    filtered_enroll = filtered_enroll[filtered_enroll['channel'] == selected_channel]
    enrolled_leads = filtered_enroll[filtered_enroll['is_converted'] == 1]['lead_id']
    filtered_students = filtered_students[filtered_students['lead_id'].isin(enrolled_leads)]
    student_ids = filtered_students['student_id']
    filtered_attendance = filtered_attendance[filtered_attendance['student_id'].isin(student_ids)]
    filtered_feedback = filtered_feedback[filtered_feedback['student_id'].isin(student_ids)]

# Header
st.markdown('<div class="main-title">Student Lifecycle & Operations Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Tracking lead acquisition, attendance retention, capstone scores, and weekly feedback.</div>', unsafe_allow_html=True)

# Top KPIs
k1, k2, k3, k4, k5 = st.columns(5)

total_leads = len(filtered_enroll)
total_conversions = int(filtered_enroll['is_converted'].sum())
conv_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0
total_spend = filtered_enroll['ad_cost'].sum()
cac = (total_spend / total_conversions) if total_conversions > 0 else 0

total_sessions = len(filtered_attendance)
present_sessions = len(filtered_attendance[filtered_attendance['status'] == 'Present'])
attendance_pct = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0

avg_capstone = filtered_students['capstone_score'].mean() if len(filtered_students) > 0 else 0

with k1:
    render_kpi("Total Leads", f"{total_leads:,}", "Inquiries", "neutral")
with k2:
    render_kpi("Enrolled Students", f"{total_conversions:,}", "Converted", "green")
with k3:
    pill_c = "green" if conv_rate >= 18 else "coral"
    render_kpi("Conversion Rate", f"{conv_rate:.1f}%", "Overall", pill_c)
with k4:
    pill_a = "green" if attendance_pct >= 80 else "coral"
    render_kpi("Avg Attendance", f"{attendance_pct:.1f}%", "Target ≥ 80%", pill_a)
with k5:
    render_kpi("Avg Capstone", f"{avg_capstone:.1f}", "Score / 100", "neutral")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# Tabs
tab_mkt, tab_att, tab_acad, tab_fb = st.tabs([
    "Marketing & Acquisition",
    "Attendance & Retention",
    "Academics & Outcomes",
    "Feedback & Sentiment"
])

# Tab 1: Marketing & Acquisition
with tab_mkt:
    mkt_summary = filtered_enroll.groupby('channel').agg(
        total_leads=('lead_id', 'count'),
        conversions=('is_converted', 'sum'),
        total_ad_cost=('ad_cost', 'sum')
    ).reset_index()
    mkt_summary['conv_rate_pct'] = (mkt_summary['conversions'] / mkt_summary['total_leads'] * 100).round(2)
    mkt_summary['cac'] = (mkt_summary['total_ad_cost'] / mkt_summary['conversions'].replace(0, pd.NA)).round(2).fillna(0.0)

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        render_chart_header("Conversion Rate by Channel (%)", "EFFICIENCY")
        chart_conv = alt.Chart(mkt_summary).mark_bar(
            color="#23242E",
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6
        ).encode(
            x=alt.X('channel:N', title='Channel', axis=alt.Axis(labelAngle=0, labelPadding=10, titlePadding=12, labelColor="#23242E", titleColor="#5C6773")),
            y=alt.Y('conv_rate_pct:Q', title='Conversion Rate (%)', axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773", titleColor="#5C6773")),
            tooltip=[
                alt.Tooltip('channel', title='Channel'),
                alt.Tooltip('total_leads', title='Total Leads'),
                alt.Tooltip('conversions', title='Enrolled'),
                alt.Tooltip('conv_rate_pct', title='Conversion Rate (%)', format='.2f')
            ]
        ).properties(height=300, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(chart_conv, use_container_width=True)

    with col_m2:
        render_chart_header("Customer Acquisition Cost (CAC in USD)", "SPEND")
        chart_cac = alt.Chart(mkt_summary).mark_bar(
            color="#F07167",
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6
        ).encode(
            x=alt.X('channel:N', title='Channel', axis=alt.Axis(labelAngle=0, labelPadding=10, titlePadding=12, labelColor="#23242E", titleColor="#5C6773")),
            y=alt.Y('cac:Q', title='CAC (Cost per Enrollment in $)', axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773", titleColor="#5C6773")),
            tooltip=[
                alt.Tooltip('channel', title='Channel'),
                alt.Tooltip('total_ad_cost', title='Total Spend ($)', format='$,.2f'),
                alt.Tooltip('conversions', title='Enrolled'),
                alt.Tooltip('cac', title='CAC ($)', format='$,.2f')
            ]
        ).properties(height=300, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(chart_cac, use_container_width=True)

    render_chart_header("Inquiries & Conversions by Postal Code", "GEO")
    postal_summary = filtered_enroll.groupby('postal_code').agg(
        inquiries=('lead_id', 'count'),
        conversions=('is_converted', 'sum'),
        spend=('ad_cost', 'sum')
    ).reset_index()
    postal_summary['conversion_pct'] = (postal_summary['conversions'] / postal_summary['inquiries'] * 100).round(1)
    postal_summary['status'] = postal_summary['conversions'].apply(
        lambda x: "Zero Conversions" if x == 0 else "Active"
    )
    postal_summary['spend'] = postal_summary['spend'].apply(lambda x: f"${x:,.2f}")
    postal_summary = postal_summary.rename(columns={
        'postal_code': 'Postal Code',
        'inquiries': 'Total Inquiries',
        'conversions': 'Enrolled Students',
        'spend': 'Total Ad Spend',
        'conversion_pct': 'Conv Rate (%)',
        'status': 'Status'
    })
    st.dataframe(
        postal_summary.sort_values(by='Total Inquiries', ascending=False),
        use_container_width=True,
        hide_index=True
    )

    render_takeaway(
        "Walk-in inquiries convert at ~18.4% with zero ad spend. YouTube and Instagram average ~18% conversion with an acquisition cost of ~$1,650 per student. Postal codes 641035 and 641045 had 0 conversions across all inquiries, indicating wasted ad spend in those two areas."
    )

# Tab 2: Attendance & Retention
with tab_att:
    sess_summary = filtered_attendance.groupby('session_number').agg(
        total_logs=('student_id', 'count'),
        present_count=('status', lambda s: (s == 'Present').sum())
    ).reset_index()
    sess_summary['attendance_rate_pct'] = (sess_summary['present_count'] / sess_summary['total_logs'] * 100).round(1)

    render_chart_header("Session Attendance Progression (Sessions 1 to 20)", "RETENTION")
    line_chart = alt.Chart(sess_summary).mark_line(
        color="#23242E",
        strokeWidth=3,
        point=alt.OverlayMarkDef(color="#F07167", size=60, filled=True)
    ).encode(
        x=alt.X('session_number:O', title='Session Number', axis=alt.Axis(labelAngle=0, labelPadding=8, titlePadding=10, labelColor="#23242E", titleColor="#5C6773")),
        y=alt.Y('attendance_rate_pct:Q', title='Attendance Rate (%)', scale=alt.Scale(domain=[50, 100]), axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773", titleColor="#5C6773")),
        tooltip=[
            alt.Tooltip('session_number', title='Session'),
            alt.Tooltip('present_count', title='Present'),
            alt.Tooltip('total_logs', title='Logged'),
            alt.Tooltip('attendance_rate_pct', title='Attendance (%)')
        ]
    ).properties(height=290, background="#FFFFFF").configure_view(strokeWidth=0)
    st.altair_chart(line_chart, use_container_width=True)

    render_chart_header("Students Below 80% Attendance Threshold", "ATTENDANCE")
    stu_att = filtered_attendance.groupby('student_id').agg(
        total_sessions=('session_number', 'count'),
        attended=('status', lambda s: (s == 'Present').sum()),
        missed=('status', lambda s: (s == 'Absent').sum())
    ).reset_index()
    stu_att['attendance_pct'] = (stu_att['attended'] / stu_att['total_sessions'] * 100).round(1)
    stu_att = stu_att.merge(filtered_students[['student_id', 'course']], on='student_id', how='left')

    stu_att['risk_level'] = stu_att['attendance_pct'].apply(
        lambda x: "Critical (<70%)" if x < 70 else ("Warning (70-79%)" if x < 80 else "Normal (≥80%)")
    )

    col_att1, col_att2 = st.columns([1, 2])
    with col_att1:
        tier_counts = stu_att['risk_level'].value_counts().reset_index()
        tier_counts.columns = ['Status', 'Student Count']
        tier_chart = alt.Chart(tier_counts).mark_bar(
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4
        ).encode(
            x=alt.X('Status:N', sort=['Critical (<70%)', 'Warning (70-79%)', 'Normal (≥80%)'], axis=alt.Axis(labelAngle=0, labelPadding=8, titlePadding=10, labelColor="#23242E")),
            y=alt.Y('Student Count:Q', axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773")),
            color=alt.Color('Status:N', scale=alt.Scale(
                domain=['Critical (<70%)', 'Warning (70-79%)', 'Normal (≥80%)'],
                range=['#F07167', '#FBBF24', '#7BC97F']
            ), legend=None)
        ).properties(height=260, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(tier_chart, use_container_width=True)

    with col_att2:
        at_risk_list = stu_att[stu_att['attendance_pct'] < 80].sort_values(by='attendance_pct').rename(columns={
            'student_id': 'Student ID',
            'course': 'Course',
            'attended': 'Present',
            'missed': 'Absent',
            'attendance_pct': 'Attendance (%)',
            'risk_level': 'Tier'
        })
        st.dataframe(
            at_risk_list[['Student ID', 'Course', 'Present', 'Absent', 'Attendance (%)', 'Tier']],
            use_container_width=True,
            hide_index=True
        )

    render_takeaway(
        "Attendance declines from 84% in Session 1 down toward 78% by Session 12. Students with attendance below 75% are highlighted above for instructor follow-up."
    )

# Tab 3: Academics & Outcomes
with tab_acad:
    col_ac1, col_ac2 = st.columns(2)

    with col_ac1:
        render_chart_header("Average Capstone Score by Course", "SCORES")
        course_perf = filtered_students.groupby('course').agg(
            students_count=('student_id', 'count'),
            avg_capstone=('capstone_score', 'mean')
        ).reset_index()
        course_perf['avg_capstone'] = course_perf['avg_capstone'].round(1)

        cap_chart = alt.Chart(course_perf).mark_bar(
            color="#23242E",
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6
        ).encode(
            x=alt.X('course:N', title='Course', axis=alt.Axis(labelAngle=0, labelPadding=10, titlePadding=12, labelColor="#23242E")),
            y=alt.Y('avg_capstone:Q', title='Avg Capstone Score', scale=alt.Scale(domain=[50, 100]), axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773")),
            tooltip=[
                alt.Tooltip('course', title='Course'),
                alt.Tooltip('students_count', title='Students'),
                alt.Tooltip('avg_capstone', title='Avg Capstone')
            ]
        ).properties(height=280, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(cap_chart, use_container_width=True)

    with col_ac2:
        render_chart_header("Mock Interview Grade Distribution", "GRADES")
        grade_dist = filtered_students['mock_grade'].value_counts().reset_index()
        grade_dist.columns = ['Grade', 'Students']

        grade_chart = alt.Chart(grade_dist).mark_bar(
            color="#7BC97F",
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6
        ).encode(
            x=alt.X('Grade:N', sort=['A+', 'A', 'B', 'C'], axis=alt.Axis(labelAngle=0, labelPadding=10, titlePadding=12, labelColor="#23242E")),
            y=alt.Y('Students:Q', title='Count', axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773")),
            tooltip=[alt.Tooltip('Grade', title='Grade'), alt.Tooltip('Students', title='Count')]
        ).properties(height=280, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(grade_chart, use_container_width=True)

    render_chart_header("Enrolled Student Registry", "STUDENTS")
    student_display = filtered_students.rename(columns={
        'student_id': 'Student ID',
        'lead_id': 'Lead ID',
        'course': 'Course',
        'enrollment_date': 'Enrollment Date',
        'capstone_score': 'Capstone Score',
        'mock_grade': 'Mock Grade',
        'tech_stack': 'Tech Stack'
    })
    st.dataframe(
        student_display[['Student ID', 'Course', 'Enrollment Date', 'Capstone Score', 'Mock Grade', 'Tech Stack']],
        use_container_width=True,
        hide_index=True
    )

    render_takeaway(
        "Average capstone scores sit between 73 and 77 across all 4 courses. Students with higher attendance consistently achieve higher scores on both the capstone and mock technical interviews."
    )

# Tab 4: Feedback & Sentiment
with tab_fb:
    col_fb1, col_fb2 = st.columns(2)

    with col_fb1:
        render_chart_header("Weekly Feedback Rating (1 - 5 Stars)", "TREND")
        week_fb = filtered_feedback.groupby('week_number').agg(
            responses=('feedback_id', 'count'),
            avg_rating=('rating', 'mean')
        ).reset_index()
        week_fb['avg_rating'] = week_fb['avg_rating'].round(2)

        chart_fb = alt.Chart(week_fb).mark_line(
            color="#23242E",
            strokeWidth=3,
            point=alt.OverlayMarkDef(color="#7BC97F", size=60, filled=True)
        ).encode(
            x=alt.X('week_number:O', title='Week', axis=alt.Axis(labelAngle=0, labelPadding=10, titlePadding=12, labelColor="#23242E")),
            y=alt.Y('avg_rating:Q', title='Avg Rating (1-5)', scale=alt.Scale(domain=[1, 5]), axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773")),
            tooltip=[
                alt.Tooltip('week_number', title='Week'),
                alt.Tooltip('responses', title='Submissions'),
                alt.Tooltip('avg_rating', title='Avg Rating')
            ]
        ).properties(height=280, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(chart_fb, use_container_width=True)

    with col_fb2:
        render_chart_header("Rating Distribution", "RATINGS")
        rating_counts = filtered_feedback['rating'].value_counts().reset_index()
        rating_counts.columns = ['Rating', 'Count']

        chart_rating = alt.Chart(rating_counts).mark_bar(
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6
        ).encode(
            x=alt.X('Rating:O', title='Stars', axis=alt.Axis(labelAngle=0, labelPadding=10, titlePadding=12, labelColor="#23242E")),
            y=alt.Y('Count:Q', title='Responses', axis=alt.Axis(gridColor="#D6E2E4", gridDash=[3, 3], labelColor="#5C6773")),
            color=alt.Color('Rating:O', scale=alt.Scale(
                domain=[1, 2, 3, 4, 5],
                range=['#F07167', '#F07167', '#FBBF24', '#7BC97F', '#23242E']
            ), legend=None),
            tooltip=[alt.Tooltip('Rating', title='Stars'), alt.Tooltip('Count', title='Count')]
        ).properties(height=280, background="#FFFFFF").configure_view(strokeWidth=0)
        st.altair_chart(chart_rating, use_container_width=True)

    render_chart_header("Student Feedback Log", "FEEDBACK")
    low_only = st.checkbox("Show only ratings ≤ 3 stars", value=False)
    fb_table = filtered_feedback.copy()
    if low_only:
        fb_table = fb_table[fb_table['rating'] <= 3]

    fb_display = fb_table.sort_values(by='rating').rename(columns={
        'feedback_id': 'Feedback ID',
        'student_id': 'Student ID',
        'week_number': 'Week',
        'rating': 'Rating',
        'comments': 'Comment'
    })
    st.dataframe(
        fb_display[['Feedback ID', 'Student ID', 'Week', 'Rating', 'Comment']],
        use_container_width=True,
        hide_index=True
    )

    render_takeaway(
        "Weekly curriculum ratings average around 3.5 out of 5. Comments from students rating 3 or below frequently mention needing more hands-on lab time for SQL window functions and Power BI DAX formulas."
    )
