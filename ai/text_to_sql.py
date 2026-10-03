import os
import re
import json
import pandas as pd
import streamlit as st
import snowflake.connector

from google import genai
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "gemini-3.5-flash-lite"


FORBIDDEN_WORDS = [
    "drop",
    "delete",
    "truncate",
    "alter",
    "update",
    "insert",
    "create",
    "replace",
    "grant",
    "revoke",
    "merge",
    "call",
    "execute",
]


EXAMPLE_QUESTIONS = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Top 5 restaurants by revenue",
    "Average delivery time by city, worst first",
    "Top 10 restaurants by average delivery time",
]


# ============================================================
# GEMINI CLIENT
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY is missing from your .env file.")
    st.stop()

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# DATABASE SCHEMA
# ============================================================

SCHEMA = """
DATABASE: ZOMATO
SCHEMA: MARTS

TABLE: FCT_ORDERS

COLUMNS:
ORDER_ID
ORDER_TIMESTAMP
ORDER_DATE
CUSTOMER_ID
RESTAURANT_ID
CITY
CUISINE
PAYMENT_METHOD
ORDER_STATUS
IS_DELIVERED
ITEMS_COUNT
SALES_QTY
SUBTOTAL
DISCOUNT
DELIVERY_FEE
GST
SALES_AMOUNT
CUSTOMER_RATING
DELIVERY_TIME_MIN


TABLE: DIM_RESTAURANTS

COLUMNS:
RESTAURANT_ID
RESTAURANT_NAME
CITY
CUISINE
RATING
COST_FOR_TWO


TABLE: DIM_CUSTOMER

COLUMNS:
CUSTOMER_ID
CUSTOMER_NAME
AGE
AGE_SEGMENT
GENDER
CITY


TABLE: MART_DAILY_CITY_REVENUE

COLUMNS:
ORDER_DATE
CITY
ORDERS
CANCEL_RATE
GMV
AOV


TABLE: MART_RESTAURANT_PERFORMANCE

COLUMNS:
RESTAURANT_ID
RESTAURANT_NAME
CITY
CUISINE
ORDERS
REVENUE
AVG_CUSTOMER_RATING
AVG_DELIVERY_MIN


TABLE: MART_DELIVERY_SLA

COLUMNS:
CITY
ORDER_HOUR
DELIVERED_ORDERS
P50
P90
"""


# ============================================================
# SNOWFLAKE CONNECTION
# ============================================================

@st.cache_resource
def get_connection():

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse="ZOMATO_WH",
        database="ZOMATO",
        schema="MARTS",
        role="ACCOUNTADMIN",
    )


# ============================================================
# GENERATE SQL
# ============================================================

def generate_sql(question):

    prompt = """
You are an expert Snowflake SQL generator for a Zomato
Data Engineering and Analytics project.

Your job is to convert the user's natural-language question
into ONE valid Snowflake SELECT query.

IMPORTANT:
Return ONLY valid JSON.

The required JSON format is:

{
    "sql": "YOUR SQL QUERY"
}

Do NOT return:
- Markdown
- ```sql
- ```json
- Explanations
- Multiple queries

DATABASE:
ZOMATO

SCHEMA:
MARTS

IMPORTANT:
Always use fully qualified table names.

Example:

ZOMATO.MARTS.MART_DAILY_CITY_REVENUE

NOT:

MART_DAILY_CITY_REVENUE


AVAILABLE TABLES
================

1. ZOMATO.MARTS.FCT_ORDERS

Columns:

ORDER_ID
ORDER_TIMESTAMP
ORDER_DATE
CUSTOMER_ID
RESTAURANT_ID
CITY
CUISINE
PAYMENT_METHOD
ORDER_STATUS
IS_DELIVERED
ITEMS_COUNT
SALES_QTY
SUBTOTAL
DISCOUNT
DELIVERY_FEE
GST
SALES_AMOUNT
CUSTOMER_RATING
DELIVERY_TIME_MIN


2. ZOMATO.MARTS.DIM_RESTAURANTS

Columns:

RESTAURANT_ID
RESTAURANT_NAME
CITY
CUISINE
RATING
COST_FOR_TWO


3. ZOMATO.MARTS.DIM_CUSTOMER

Columns:

CUSTOMER_ID
CUSTOMER_NAME
AGE
AGE_SEGMENT
GENDER
CITY


4. ZOMATO.MARTS.MART_DAILY_CITY_REVENUE

Columns:

ORDER_DATE
CITY
ORDERS
CANCEL_RATE
GMV
AOV


5. ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE

Columns:

RESTAURANT_ID
RESTAURANT_NAME
CITY
CUISINE
ORDERS
REVENUE
AVG_CUSTOMER_RATING
AVG_DELIVERY_MIN


6. ZOMATO.MARTS.MART_DELIVERY_SLA

Columns:

CITY
ORDER_HOUR
DELIVERED_ORDERS
P50
P90


BUSINESS RULES
==============

1. For city GMV questions:

Use:

ZOMATO.MARTS.MART_DAILY_CITY_REVENUE


2. For city revenue questions:

Use:

ZOMATO.MARTS.MART_DAILY_CITY_REVENUE


3. For restaurant revenue questions:

Use:

ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE


4. For restaurant order questions:

Use:

ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE


5. For cuisine order questions:

Use:

ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE


6. For restaurant rating questions:

Use:

ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE


7. For restaurant delivery time questions:

Use:

ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE


8. For delivery SLA questions:

Use:

ZOMATO.MARTS.MART_DELIVERY_SLA


9. For delivery percentile questions:

Use:

ZOMATO.MARTS.MART_DELIVERY_SLA


10. For detailed order-level questions:

Use:

ZOMATO.MARTS.FCT_ORDERS


11. For restaurant master information:

Use:

ZOMATO.MARTS.DIM_RESTAURANTS


12. For customer information:

Use:

ZOMATO.MARTS.DIM_CUSTOMER


IMPORTANT COLUMN RULES
======================

MART_DELIVERY_SLA contains:

P50
P90

DO NOT use:

P50_DELIVERY_MIN
P90_DELIVERY_MIN


The correct table name is:

MART_DAILY_CITY_REVENUE

DO NOT use:

MART_DAILY_CITY_REVENUNE


The correct table name is:

DIM_RESTAURANTS

DO NOT use:

DIM_RESTAURANT


The correct column for restaurant delivery time is:

AVG_DELIVERY_MIN


The correct columns for restaurant performance are:

ORDERS
REVENUE
AVG_CUSTOMER_RATING
AVG_DELIVERY_MIN


EXAMPLES
========

Question:
Top 10 cities by GMV

SQL:

SELECT
    CITY,
    SUM(GMV) AS GMV
FROM ZOMATO.MARTS.MART_DAILY_CITY_REVENUE
GROUP BY CITY
ORDER BY GMV DESC
LIMIT 10;


Question:
Top 5 restaurants by revenue

SQL:

SELECT
    RESTAURANT_NAME,
    CITY,
    REVENUE
FROM ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE
ORDER BY REVENUE DESC
LIMIT 5;


Question:
Average delivery time by city, worst first

SQL:

SELECT
    CITY,
    AVG(P50) AS AVG_DELIVERY_TIME
FROM ZOMATO.MARTS.MART_DELIVERY_SLA
GROUP BY CITY
ORDER BY AVG_DELIVERY_TIME DESC;


Question:
Which cuisine has the most orders?

SQL:

SELECT
    CUISINE,
    SUM(ORDERS) AS TOTAL_ORDERS
FROM ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE
GROUP BY CUISINE
ORDER BY TOTAL_ORDERS DESC
LIMIT 1;


Question:
Top 10 restaurants by average delivery time

SQL:

SELECT
    RESTAURANT_NAME,
    CITY,
    AVG_DELIVERY_MIN
FROM ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE
ORDER BY AVG_DELIVERY_MIN DESC
LIMIT 10;


Question:
Show revenue by city

SQL:

SELECT
    CITY,
    SUM(GMV) AS TOTAL_REVENUE
FROM ZOMATO.MARTS.MART_DAILY_CITY_REVENUE
GROUP BY CITY
ORDER BY TOTAL_REVENUE DESC;


USER QUESTION:
""" + question

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "temperature": 0,
            "response_mime_type": "application/json"
        }
    )

    answer = response.text.strip()

    # Remove accidental markdown
    answer = answer.replace("```json", "")
    answer = answer.replace("```", "")
    answer = answer.strip()

    # Parse JSON
    data = json.loads(answer)

    sql = data.get("sql", "").strip()

    if not sql:
        raise ValueError(
            "Gemini returned an empty SQL query."
        )

    # Remove trailing semicolon
    sql = sql.rstrip(";").strip()

    return sql


# ============================================================
# SQL SAFETY CHECK
# ============================================================

def is_safe(sql):

    if not sql:
        return False, "SQL query is empty."

    cleaned = sql.strip()

    lowered = cleaned.lower()

    # Must start with SELECT or WITH
    if not (
        lowered.startswith("select")
        or lowered.startswith("with")
    ):
        return False, "Only SELECT queries are allowed."

    # No multiple statements
    if ";" in cleaned:
        return False, "Multiple SQL statements are not allowed."

    # No comments
    if "--" in cleaned:
        return False, "SQL comments are not allowed."

    if "/*" in cleaned:
        return False, "SQL comments are not allowed."

    if "*/" in cleaned:
        return False, "SQL comments are not allowed."

    # Dangerous SQL keywords
    for word in FORBIDDEN_WORDS:

        pattern = r"\b" + re.escape(word) + r"\b"

        if re.search(pattern, lowered):

            return False, (
                f"Forbidden SQL keyword detected: {word}"
            )

    return True, ""


# ============================================================
# RUN QUERY
# ============================================================

def run_query(sql):

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        # Explicitly set database
        cursor.execute(
            "USE DATABASE ZOMATO"
        )

        # Explicitly set schema
        cursor.execute(
            "USE SCHEMA ZOMATO.MARTS"
        )

        # Execute generated SQL
        result = cursor.execute(
            sql
        )

        # Convert result directly to pandas
        df = result.fetch_pandas_all()

        return df

    finally:

        if cursor is not None:

            cursor.close()

        # Do not close cached connection here.


# ============================================================
# STREAMLIT PAGE
# ============================================================

st.set_page_config(
    page_title="Zomato AI Analytics",
    page_icon="🍽️",
    layout="wide",
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🍽️ Zomato AI Analytics"
)

st.caption(
    f"Ask in English → {MODEL} generates SQL → "
    "Snowflake executes it"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "Example Questions"
    )

    for q in EXAMPLE_QUESTIONS:

        if st.button(
            q,
            use_container_width=True
        ):

            st.session_state["question"] = q


# ============================================================
# QUESTION INPUT
# ============================================================

question = st.text_input(
    "Ask your question:",
    value=st.session_state.get(
        "question",
        ""
    ),
    placeholder=(
        "Example: Top 10 cities by GMV"
    ),
)


# ============================================================
# GENERATE AND RUN
# ============================================================

if st.button(
    "🚀 Generate & Run SQL",
    type="primary"
):

    if not question.strip():

        st.warning(
            "Please enter a question."
        )

        st.stop()

    # --------------------------------------------------------
    # GENERATE SQL
    # --------------------------------------------------------

    try:

        with st.spinner(
            "Generating SQL with Gemini..."
        ):

            sql = generate_sql(
                question
            )

    except json.JSONDecodeError:

        st.error(
            "Gemini returned invalid JSON."
        )

        st.stop()

    except Exception as e:

        st.error(
            f"Error generating SQL: {e}"
        )

        st.stop()


    # --------------------------------------------------------
    # SHOW GENERATED SQL
    # --------------------------------------------------------

    st.subheader(
        "Generated SQL"
    )

    st.code(
        sql,
        language="sql"
    )


    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    safe, message = is_safe(
        sql
    )

    if not safe:

        st.error(
            f"SQL blocked: {message}"
        )

        st.stop()


    # --------------------------------------------------------
    # EXECUTE SQL
    # --------------------------------------------------------

    try:

        with st.spinner(
            "Running query on Snowflake..."
        ):

            df = run_query(
                sql
            )

    except Exception as e:

        st.error(
            "Snowflake query failed."
        )

        st.code(
            str(e)
        )

        st.stop()


    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    st.success(
        f"{len(df)} rows returned"
    )

    st.subheader(
        "Results"
    )

    if df.empty:

        st.info(
            "The query returned no results."
        )

    else:

        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True
        )


        # ----------------------------------------------------
        # AUTOMATIC VISUALIZATION
        # ----------------------------------------------------

        if (
            len(df.columns) == 2
            and len(df) > 0
            and pd.api.types.is_numeric_dtype(
                df.iloc[:, 1]
            )
        ):

            st.subheader(
                "Visualization"
            )

            st.bar_chart(
                df,
                x=df.columns[0],
                y=df.columns[1]
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Zomato AI Analytics | "
    "S3 → Snowflake → dbt → Gemini → Streamlit"
)