# 🍽️ Zomato End-to-End Data Engineering & AI Platform

An end-to-end data engineering and AI analytics platform that takes Zomato-style food delivery data from raw CSV files to a cloud data warehouse and finally exposes analytics and AI-powered applications.

The pipeline follows:

**Zomato Dataset → Amazon S3 → Snowflake → dbt → Airflow → AI → Streamlit**

---

## 🏗️ Architecture

![Zomato Data Engineering Architecture](docs/architecture.png)

The platform follows a medallion-style architecture:

```text
Zomato Dataset
      ↓
 Amazon S3
      ↓
Snowflake RAW
   Bronze Layer
      ↓
dbt STAGING
   Silver Layer
      ↓
dbt MARTS
    Gold Layer
      ↓
Streamlit / SnowSight