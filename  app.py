"""Customer Churn Dashboard - Streamlit UI for the Big Data capstone.
Reads outputs produced by the pipeline (HDFS -> Hive -> Spark -> HBase):
  results/spark_churn_by_*.csv   Spark aggregations
  results/churn_risk_scores.csv  Spark MLlib risk scores (all customers)
  results/model_metrics.json     model AUC / accuracy
  data/sample/churn.csv          raw dataset (for KPIs)
"""
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
RES, RAW = ROOT / "results", ROOT / "data" / "sample" / "churn.csv"
ORDERS = {"tenure_group": ["0-12", "13-24", "25-48", "49+"], "spend_category": ["Low", "Medium", "High"]}
SEGMENTS = {"Contract type": "contract", "Tenure group (months)": "tenure_group",
            "Internet service": "internetservice", "Payment method": "paymentmethod",
            "Monthly spend": "spend_category"}

st.set_page_config(page_title="Customer Churn Dashboard", page_icon="📉", layout="wide")


@st.cache_data
def load_raw():
    df = pd.read_csv(RAW)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0.0)
    df["churned"] = (df["Churn"] == "Yes").astype(int)
    return df


@st.cache_data
def load_csv(path):
    return pd.read_csv(path) if Path(path).exists() else None


def load_metrics():
    f = RES / "model_metrics.json"
    return json.loads(f.read_text()) if f.exists() else {}


def band(risk):
    return "High" if risk >= 0.6 else "Medium" if risk >= 0.3 else "Low"


def bar(df):
    col = df.columns[0]
    sort = ORDERS.get(col, "-y")
    base = alt.Chart(df).encode(x=alt.X(col, sort=sort, title=None, axis=alt.Axis(labelAngle=0)),
                                y=alt.Y("churn_pct", title="Churn %"),
                                tooltip=[col, "customers", "churn_pct", "avg_monthly"])
    return base.mark_bar(color="#c4552d") + base.mark_text(dy=-8).encode(text=alt.Text("churn_pct:Q", format=".1f"))


st.title("📉 Customer Churn Dashboard")
st.caption("Big Data Analytics Capstone · HDFS → Hive → Spark/PySpark → HBase")

if not RAW.exists():
    st.error(f"Dataset not found at {RAW}. Run this app from the project repository.")
    st.stop()

raw, metrics = load_raw(), load_metrics()
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Churn drivers", "Customer risk", "About the pipeline"])

with tab1:
    c = st.columns(5)
    c[0].metric("Customers", f"{len(raw):,}")
    c[1].metric("Churned", f"{raw.churned.sum():,}")
    c[2].metric("Churn rate", f"{raw.churned.mean() * 100:.2f}%")
    c[3].metric("Model AUC", metrics.get("auc", "n/a"))
    c[4].metric("Model accuracy", f"{metrics['accuracy'] * 100:.1f}%" if "accuracy" in metrics else "n/a")
    st.subheader("Churned vs retained customers")
    cmp = raw.groupby("Churn").agg(customers=("customerID", "count"), avg_monthly_charge=("MonthlyCharges", "mean"),
                                   avg_tenure_months=("tenure", "mean")).round(2)
    st.dataframe(cmp, width="stretch")
    st.subheader("Key insights (from Spark results)")
    for label, name in SEGMENTS.items():
        seg = load_csv(RES / f"spark_churn_by_{name}.csv")
        if seg is not None:
            top = seg.sort_values("churn_pct", ascending=False).iloc[0]
            st.write(f"- **{label}:** highest churn is **{top.iloc[0]}** at **{top['churn_pct']:.2f}%** ({int(top['customers']):,} customers)")

with tab2:
    choice = st.radio("Segment", list(SEGMENTS), horizontal=True)
    seg = load_csv(RES / f"spark_churn_by_{SEGMENTS[choice]}.csv")
    if seg is None:
        st.warning("Spark result file not found in results/. Run the Spark notebook first.")
    else:
        st.altair_chart(bar(seg), width="stretch")
        st.dataframe(seg, width="stretch", hide_index=True)

with tab4:
    st.markdown("""
**Flow:** `churn.csv` → **HDFS** (`/data/churn/raw`) → **Hive** (external table `churn_analytics.customers`)
→ **Spark/PySpark** (cleaning, aggregations, logistic regression) → **HBase** (`churn_risk`, row key = customerID).

- Dataset: IBM Telco Customer Churn, 7,043 rows × 21 columns.
- Cleaning: 11 blank `TotalCharges` values set to 0; derived `churn_flag`, `tenure_group`, `spend_category`.
- Model: Spark MLlib logistic regression, 80/20 split.
- This dashboard is a presentation layer that reads the exported pipeline outputs from the `results/` folder.
""")

with tab3:
    scores = load_csv(RES / "churn_risk_scores.csv")
    if scores is None:
        st.info("`results/churn_risk_scores.csv` not found. Export it from the Spark notebook (see project README).")
    else:
        scores["band"] = scores["risk"].apply(band)
        st.subheader("Look up a customer")
        cid = st.selectbox("Customer ID (type to search)", scores["customerID"].tolist(),
                           index=None, placeholder="e.g. 5150-ITWWB")
        if cid:
            r = scores[scores.customerID == cid].iloc[0]
            a, b, d, e = st.columns(4)
            a.metric("Churn risk", f"{r.risk * 100:.1f}%")
            b.metric("Risk band", r.band)
            d.metric("Contract", r.Contract)
            e.metric("Tenure (months)", int(r.tenure))
            st.progress(float(min(max(r.risk, 0), 1)))
            st.caption(f"{r.InternetService} · {r.PaymentMethod} · ${r.MonthlyCharges:.2f}/month · actual status: "
                       f"{'Churned' if r.Churn == 'Yes' else 'Active'}")
        st.subheader("Active customers most at risk")
        f1, f2 = st.columns(2)
        contracts = f1.multiselect("Contract", sorted(scores.Contract.unique()), default=list(scores.Contract.unique()))
        min_risk = f2.slider("Minimum risk", 0.0, 1.0, 0.6, 0.05)
        act = scores[(scores.Churn == "No") & scores.Contract.isin(contracts) & (scores.risk >= min_risk)]
        act = act.sort_values("risk", ascending=False)
        st.write(f"{len(act):,} customers match")
        show = act[["customerID", "risk", "band", "Contract", "tenure", "MonthlyCharges", "InternetService", "PaymentMethod"]]
        st.dataframe(show.head(50), width="stretch", hide_index=True)
        st.download_button("Download list (CSV)", show.to_csv(index=False), "at_risk_customers.csv", "text/csv")
        st.caption("The top 20 are also stored in HBase table `churn_risk` for instant lookup.")
