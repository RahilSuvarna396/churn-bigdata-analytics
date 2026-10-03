USE churn_analytics;

-- Q1 Overall churn rate
SELECT COUNT(*) AS customers, SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END) AS churned,
 ROUND(100.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_pct FROM customers;

-- Q2 Churn by contract type
SELECT Contract, COUNT(*) AS customers,
 ROUND(100.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_pct
FROM customers GROUP BY Contract ORDER BY churn_pct DESC;

-- Q3 Churn by internet service
SELECT InternetService, COUNT(*) AS customers,
 ROUND(100.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_pct
FROM customers GROUP BY InternetService ORDER BY churn_pct DESC;

-- Q4 Churn by payment method
SELECT PaymentMethod, COUNT(*) AS customers,
 ROUND(100.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_pct
FROM customers GROUP BY PaymentMethod ORDER BY churn_pct DESC;

-- Q5 Churn by tenure group
SELECT CASE WHEN tenure<=12 THEN '0-12' WHEN tenure<=24 THEN '13-24'
 WHEN tenure<=48 THEN '25-48' ELSE '49+' END AS tenure_group,
 COUNT(*) AS customers,
 ROUND(100.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_pct
FROM customers GROUP BY CASE WHEN tenure<=12 THEN '0-12' WHEN tenure<=24 THEN '13-24'
 WHEN tenure<=48 THEN '25-48' ELSE '49+' END ORDER BY churn_pct DESC;

-- Q6 Average monthly charge: churned vs retained
SELECT Churn, ROUND(AVG(MonthlyCharges),2) AS avg_monthly, ROUND(AVG(tenure),1) AS avg_tenure
FROM customers GROUP BY Churn;