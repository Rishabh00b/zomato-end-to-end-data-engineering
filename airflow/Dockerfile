# Airflow 3.x image + Snowflake provider + FAB auth (for admin/admin login) + dbt venv + openai.
# Bump the tag to the newest 3.x if you like (e.g. 3.0.4 / 3.1.x).
FROM apache/airflow:3.0.3

# Providers: snowflake (COPY task), fab (classic username/password login), openai (AI task).
RUN pip install --no-cache-dir \
      apache-airflow-providers-snowflake \
      apache-airflow-providers-fab \
      openai

# dbt in its own venv so it never clashes with Airflow's deps. DAG calls /opt/airflow/dbt_venv/bin/dbt
RUN python -m venv /opt/airflow/dbt_venv && \
    /opt/airflow/dbt_venv/bin/pip install --no-cache-dir "dbt-snowflake==1.8.*"