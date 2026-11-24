# Dashboard Specifications & Visual Wireframes

This document details the multi-page BI layout design for the Student Lifecycle Analytics Platform.

---

## Page 1: Executive & Marketing Acquisition Funnel

### Purpose
Analyze lead sources, advertising spend efficiency, conversion velocity, and regional demand.

### Layout & Visuals
1. **Top KPI Ribbon:**
   - Total Leads `[Total Leads]`
   - Total Enrollments `[Total Enrolled Students]`
   - Conversion Rate % `[Conversion Rate %]`
   - Total Ad Spend `[Total Marketing Spend]`
   - Customer Acquisition Cost `[CAC]`
2. **Channel Performance Matrix (Bar + Line Combo Chart):**
   - **X-axis:** Marketing Channel (`Instagram`, `YouTube`, `Walk-in`)
   - **Column Values:** Ad Spend (USD)
   - **Line Values:** Conversion Rate (%)
3. **Regional Lead Heat Table (Matrix Visual):**
   - **Rows:** Postal Code
   - **Columns:** Total Inquiries, Enrolled, Ad Spend, Conversion Rate (%)
   - **Conditional Formatting:** Red highlighting for Dead Zones (0% conversion).
4. **Global Slicers:**
   - Date Range (Inquiry Date)
   - Course Interest (`dim_courses[course_name]`)

---

## Page 2: Student Attendance, Engagement & Retention

### Purpose
Monitor cohort participation in real time, identify dropout warning signs, and analyze session-by-session retention.

### Layout & Visuals
1. **Top KPI Ribbon:**
   - Total Active Enrolled Students
   - Overall Attendance Rate `[Attendance Rate %]`
   - Sessions Scheduled vs Attended
   - At-Risk Students Count `[At-Risk Student Count]` (< 75% attendance)
2. **Session Progression Retention Curve (Line Chart):**
   - **X-axis:** Session Number (1 to 20)
   - **Y-axis:** Attendance Rate (%)
   - **Goal Line:** Target threshold of 80%
3. **At-Risk Student Action Board (Table Visual):**
   - **Columns:** Student ID, Enrolled Course, Attended Sessions, Missed Sessions, Attendance %, Risk Level (`Critical`, `Warning`)
   - **Action:** Exportable for student success advisors to reach out.
4. **Global Slicers:**
   - Course Name
   - Session Date

---

## Page 3: Academic Outcomes & Curriculum Feedback

### Purpose
Evaluate student exit readiness, correlate attendance with capstone scores, and analyze curriculum feedback.

### Layout & Visuals
1. **Top KPI Ribbon:**
   - Average Capstone Score `[Average Capstone Score]`
   - High Grade Ratio (% A/A+) `[High Achiever Ratio %]`
   - Average Student Feedback Rating `[Average Curriculum Rating]` (out of 5)
2. **Attendance vs Capstone Score (Scatter Plot):**
   - **X-axis:** Attendance %
   - **Y-axis:** Capstone Score (0 to 100)
   - **Trendline:** Shows positive linear correlation between session attendance and exit score.
3. **Mock Interview Grade Distribution (Donut Chart):**
   - **Legend:** A+, A, B, C
   - **Values:** Student Count
4. **Weekly Feedback Rating Trend (Bar Chart):**
   - **X-axis:** Week Number (Week 1 to 8)
   - **Y-axis:** Average Rating (1-5)
5. **Qualitative Comment Log (Table Visual with Slicer for Low Ratings):**
   - Shows verbatim student feedback where rating <= 3 for faculty curriculum improvements.
