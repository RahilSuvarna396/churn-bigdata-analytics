# Customer Churn Prediction - Big Data Analytics

## Problem
Identify churn patterns and score churn risk for telecom customers.

## Architecture
churn.csv -> HDFS -> Hive -> Spark/PySpark (MLlib) -> HBase

## Dataset
IBM Telco Customer Churn - 7,043 rows, 21 columns, 26.5% churn.

## Setup
1. Docker Desktop (Mac M2: enable Rosetta, 10 GB+ memory)
2. In bigdata-docker: docker compose --profile full up -d

## Execution
1. HDFS: hdfs/hdfs_commands.txt
2. Hive: hive/01_create_table.sql then hive/02_analysis_queries.sql in Beeline
3. Spark: spark/churn_analysis.ipynb in Jupyter (localhost:8888)
4. HBase: hbase/hbase_commands.txt and hbase/hbase_puts.txt

## Key results
- Overall churn 26.54%
- Month-to-month 42.71% vs two-year 2.83%
- Fiber optic 41.89%; electronic check 45.29%; first-12-months 47.44%
- Churned customers pay more (74.44 vs 61.27) and leave at 18 months on average
- Logistic regression model: AUC 0.843, accuracy 80.7%
- Top 20 active at-risk customers stored in HBase (table churn_risk)

## Author
Rahil - all five roles (HDFS, Hive, Spark, HBase, Integration)
