CREATE DATABASE IF NOT EXISTS churn_analytics;
USE churn_analytics;

CREATE EXTERNAL TABLE IF NOT EXISTS customers (
  customerID STRING, gender STRING, SeniorCitizen INT, Partner STRING,
  Dependents STRING, tenure INT, PhoneService STRING, MultipleLines STRING,
  InternetService STRING, OnlineSecurity STRING, OnlineBackup STRING,
  DeviceProtection STRING, TechSupport STRING, StreamingTV STRING,
  StreamingMovies STRING, Contract STRING, PaperlessBilling STRING,
  PaymentMethod STRING, MonthlyCharges DOUBLE, TotalCharges STRING, Churn STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/data/churn/raw/'
TBLPROPERTIES ("skip.header.line.count"="1");

