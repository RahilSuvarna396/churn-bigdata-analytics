"""Customer Churn Dashboard - Big Data capstone (HDFS -> Hive -> Spark -> HBase)."""
import json, re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ---------- paths (works whether app.py is at repo root or in a subfolder) ----------
HERE = Path(__file__).resolve().parent
ROOT = next((p for p in (HERE, HERE.parent) if (p / "data" / "sample" / "churn.csv").exists()), HERE)
RES, RAW = ROOT / "results", ROOT / "data" / "sample" / "churn.csv"

# ---------- palette ----------
CORAL, TEAL, AMBER, BLUE, NAVY = "#FF6B6B", "#2EC4B6", "#FFB703", "#4D96FF", "#0B132B"
SCALE = alt.Scale(range=[TEAL, AMBER, CORAL])
ORDERS = {"tenure_group": ["0-12", "13-24", "25-48", "49+"], "spend_category": ["Low", "Medium", "High"]}
SEGMENTS = {"Contract type": "contract", "Tenure group (months)": "tenure_group", "Internet service": "internetservice",
            "Payment method": "paymentmethod", "Monthly spend": "spend_category"}
DEFAULT_METRICS = {"auc": 0.8428, "accuracy": 0.8074}   # from the Spark MLlib run

st.set_page_config(page_title="Customer Churn Dashboard", page_icon="📉", layout="wide")
st.markdown("""<style>
.block-container{padding-top:2rem;max-width:1250px}
.kpi{background:linear-gradient(135deg,#1C2541,#243B6B);border-radius:16px;padding:16px 20px;border-left:6px solid var(--c)}
.kpi small{color:#9FB3D1;letter-spacing:.07em;text-transform:uppercase;font-size:.7rem}
.kpi h2{margin:.15rem 0 0 0;font-size:1.9rem;color:#F8FAFC}
.hero{background:linear-gradient(90deg,#FF6B6B33,#2EC4B633);border-radius:16px;padding:18px 24px;margin-bottom:14px}
.hero h1{margin:0;font-size:2.1rem}.hero p{margin:.2rem 0 0 0;color:#9FB3D1}
</style>""", unsafe_allow_html=True)


def kpi(col, label, value, color):
    col.markdown(f'<div class="kpi" style="--c:{color}"><small>{label}</small><h2>{value}</h2></div>', unsafe_allow_html=True)


@st.cache_data
def load_raw():
    d = pd.read_csv(RAW)
    d["TotalCharges"] = pd.to_numeric(d["TotalCharges"], errors="coerce").fillna(0.0)
    d["churned"] = (d["Churn"] == "Yes").astype(int)
    d["tenure_group"] = pd.cut(d.tenure, [-1, 12, 24, 48, 999], labels=ORDERS["tenure_group"]).astype(str)
    return d


@st.cache_data
def load_csv(path):
    return pd.read_csv(path) if Path(path).exists() else None


@st.cache_data
def load_scores(raw):
    """Full Spark scores if exported, otherwise the top-20 customers stored in HBase."""
    full = load_csv(RES / "churn_risk_scores.csv")
    if full is not None:
        return full, True
    f = ROOT / "hbase" / "hbase_puts.txt"
    if not f.exists():
        return None, False
    rows = re.findall(r"put 'churn_risk','([^']+)','risk:score','([\d.]+)'", f.read_text())
    top = pd.DataFrame(rows, columns=["customerID", "risk"]).astype({"risk": float})
    return top.merge(raw[["customerID", "Contract", "InternetService", "PaymentMethod", "tenure", "MonthlyCharges", "Churn"]],
                     on="customerID"), False


def band(r):
    return "High" if r >= 0.6 else "Medium" if r >= 0.3 else "Low"


raw = load_raw()
overall = raw.churned.mean() * 100
f = RES / "model_metrics.json"
metrics = {**DEFAULT_METRICS, **(json.loads(f.read_text()) if f.exists() else {})}

st.markdown('<div class="hero"><h1>📉 Customer Churn Dashboard</h1>'
            '<p>Big Data Analytics Capstone · HDFS → Hive → Spark/PySpark → HBase</p></div>', unsafe_allow_html=True)
t1, t2, t3, t4, t5 = st.tabs(["Overview", "Churn drivers", "Deep dive", "Customer risk", "About"])

# ================= Overview =================
with t1:
    c = st.columns(5)
    kpi(c[0], "Customers", f"{len(raw):,}", BLUE)
    kpi(c[1], "Churned", f"{raw.churned.sum():,}", CORAL)
    kpi(c[2], "Churn rate", f"{overall:.2f}%", AMBER)
    kpi(c[3], "Model AUC", f"{metrics['auc']:.3f}", TEAL)
    kpi(c[4], "Accuracy", f"{metrics['accuracy'] * 100:.1f}%", TEAL)
    st.write("")
    a, b = st.columns([1, 1.3])
    with a:
        st.subheader("Churn split")
        sp = raw.Churn.map({"Yes": "Churned", "No": "Retained"}).value_counts().reset_index()
        sp.columns = ["status", "customers"]
        st.altair_chart(alt.Chart(sp).mark_arc(innerRadius=70, outerRadius=120).encode(
            theta="customers:Q", color=alt.Color("status:N", scale=alt.Scale(domain=["Retained", "Churned"], range=[TEAL, CORAL]),
                                                 legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["status", "customers"]).properties(height=300), width="stretch")
    with b:
        st.subheader("What drives churn (Spark results)")
        for label, name in SEGMENTS.items():
            seg = load_csv(RES / f"spark_churn_by_{name}.csv")
            if seg is not None:
                top = seg.sort_values("churn_pct", ascending=False).iloc[0]
                st.markdown(f"🔸 **{label}:** highest churn in **{top.iloc[0]}** → **{top['churn_pct']:.1f}%** "
                            f"({int(top['customers']):,} customers)")
        g = raw.groupby("Churn").agg(m=("MonthlyCharges", "mean"), t=("tenure", "mean"))
        st.markdown(f"🔸 **Churned customers** pay **${g.m['Yes']:.2f}**/month (retained: ${g.m['No']:.2f}) "
                    f"and leave after **{g.t['Yes']:.0f}** months on average (retained: {g.t['No']:.0f}).")

# ================= Churn drivers (Spark output) =================
with t2:
    st.caption(f"Churn % per segment from the Spark aggregations. Dashed line = overall churn ({overall:.1f}%).")
    cols = st.columns(2)
    for i, (label, name) in enumerate(SEGMENTS.items()):
        seg = load_csv(RES / f"spark_churn_by_{name}.csv")
        if seg is None:
            continue
        col = seg.columns[0]
        base = alt.Chart(seg).encode(x=alt.X(col, sort=ORDERS.get(col, "-y"), title=None, axis=alt.Axis(labelAngle=0)),
                                     y=alt.Y("churn_pct", title="Churn %"), tooltip=[col, "customers", "churn_pct", "avg_monthly"])
        bars = base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            color=alt.Color("churn_pct:Q", scale=SCALE, legend=None))
        labels = base.mark_text(dy=-9, fontWeight="bold").encode(text=alt.Text("churn_pct:Q", format=".1f"))
        rule = alt.Chart(pd.DataFrame({"y": [overall]})).mark_rule(strokeDash=[6, 4], color="#CBD5E1").encode(y="y:Q")
        with cols[i % 2]:
            st.subheader(label)
            st.altair_chart((bars + labels + rule).properties(height=300), width="stretch")

# ================= Deep dive (dataset) =================
with t3:
    st.caption("Extra exploration computed from the dataset.")
    a, b = st.columns(2)
    with a:
        st.subheader("Contract × tenure heatmap")
        hm = raw.groupby(["Contract", "tenure_group"]).churned.mean().mul(100).round(1).reset_index(name="churn_pct")
        base = alt.Chart(hm).encode(x=alt.X("tenure_group:N", sort=ORDERS["tenure_group"], title="Tenure (months)",
                                            axis=alt.Axis(labelAngle=0)), y=alt.Y("Contract:N", title=None))
        st.altair_chart((base.mark_rect(cornerRadius=6).encode(color=alt.Color("churn_pct:Q", scale=SCALE, legend=None))
                         + base.mark_text(fontWeight="bold", color=NAVY).encode(text=alt.Text("churn_pct:Q", format=".1f"))
                         ).properties(height=260), width="stretch")
    with b:
        st.subheader("Churn rate by tenure month")
        tm = raw.groupby("tenure").churned.mean().mul(100).reset_index(name="churn_pct")
        st.altair_chart(alt.Chart(tm).mark_area(line={"color": CORAL}, color=alt.Gradient(
            gradient="linear", stops=[alt.GradientStop(color=CORAL + "11", offset=0), alt.GradientStop(color=CORAL, offset=1)],
            x1=1, x2=1, y1=1, y2=0)).encode(x=alt.X("tenure:Q", title="Months with company"),
                                           y=alt.Y("churn_pct:Q", title="Churn %"), tooltip=["tenure", "churn_pct"]
                                           ).properties(height=260), width="stretch")
    a, b = st.columns(2)
    with a:
        st.subheader("Monthly charges: churned vs retained")
        st.altair_chart(alt.Chart(raw).mark_bar(opacity=.75).encode(
            x=alt.X("MonthlyCharges:Q", bin=alt.Bin(maxbins=30), title="Monthly charge ($)"),
            y=alt.Y("count()", stack=None, title="Customers"),
            color=alt.Color("Churn:N", scale=alt.Scale(domain=["No", "Yes"], range=[TEAL, CORAL]),
                            legend=alt.Legend(orient="top", title=None))).properties(height=280), width="stretch")
    with b:
        st.subheader("Add-on services and churn")
        svc = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]
        m = raw.melt(id_vars="churned", value_vars=svc, var_name="service", value_name="has")
        m = m[m.has.isin(["Yes", "No"])].groupby(["service", "has"]).churned.mean().mul(100).round(1).reset_index(name="churn_pct")
        st.altair_chart(alt.Chart(m).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("service:N", title=None, axis=alt.Axis(labelAngle=-25)), xOffset="has:N",
            y=alt.Y("churn_pct:Q", title="Churn %"),
            color=alt.Color("has:N", scale=alt.Scale(domain=["Yes", "No"], range=[TEAL, CORAL]),
                            legend=alt.Legend(orient="top", title="Has service")),
            tooltip=["service", "has", "churn_pct"]).properties(height=280), width="stretch")

# ================= Customer risk =================
with t4:
    scores, full = load_scores(raw)
    if scores is None:
        st.info("No risk scores found. Add `results/churn_risk_scores.csv` or `hbase/hbase_puts.txt` to the repository.")
    else:
        scores = scores.assign(band=scores["risk"].apply(band))
        if not full:
            st.info("Showing the **top 20 at-risk customers stored in HBase** (`churn_risk`). "
                    "Export all scores from Spark to see every customer.")
        else:
            act = scores[scores.Churn == "No"]
            c = st.columns(3)
            kpi(c[0], "High risk (active)", f"{(act.band == 'High').sum():,}", CORAL)
            kpi(c[1], "Medium risk (active)", f"{(act.band == 'Medium').sum():,}", AMBER)
            kpi(c[2], "Low risk (active)", f"{(act.band == 'Low').sum():,}", TEAL)
            st.subheader("Risk score distribution (active customers)")
            st.altair_chart(alt.Chart(act).mark_bar().encode(
                x=alt.X("risk:Q", bin=alt.Bin(step=0.05), title="Predicted churn probability"), y=alt.Y("count()", title="Customers"),
                color=alt.Color("risk:Q", bin=alt.Bin(step=0.05), scale=SCALE, legend=None)).properties(height=260), width="stretch")
        st.subheader("Look up a customer")
        cid = st.selectbox("Customer ID (type to search)", scores.customerID.tolist(), index=None, placeholder="e.g. 5150-ITWWB")
        if cid:
            r = scores[scores.customerID == cid].iloc[0]
            c = st.columns(4)
            kpi(c[0], "Churn risk", f"{r.risk * 100:.1f}%", CORAL if r.risk >= .6 else AMBER if r.risk >= .3 else TEAL)
            kpi(c[1], "Risk band", r.band, BLUE)
            kpi(c[2], "Contract", r.Contract, BLUE)
            kpi(c[3], "Tenure (months)", int(r.tenure), BLUE)
            st.progress(float(min(max(r.risk, 0), 1)))
        st.subheader("Most at-risk customers")
        pool = scores if not full else scores[scores.Churn == "No"]
        view = pool.sort_values("risk", ascending=False).head(50)[["customerID", "risk", "band", "Contract", "tenure", "MonthlyCharges", "PaymentMethod"]]
        st.dataframe(view, hide_index=True, width="stretch", column_config={
            "risk": st.column_config.ProgressColumn("Churn risk", min_value=0, max_value=1, format="%.2f"),
            "MonthlyCharges": st.column_config.NumberColumn("Monthly $", format="$%.2f")})
        st.download_button("Download list (CSV)", view.to_csv(index=False), "at_risk_customers.csv", "text/csv")

# ================= About =================
with t5:
    st.markdown("""
**Flow:** `churn.csv` → **HDFS** (`/data/churn/raw`) → **Hive** (external table `churn_analytics.customers`)
→ **Spark/PySpark** (cleaning, aggregations, logistic regression) → **HBase** (`churn_risk`, row key = customerID).

- **Dataset:** IBM Telco Customer Churn, 7,043 rows × 21 columns.
- **Cleaning:** 11 blank `TotalCharges` values set to 0; derived `churn_flag`, `tenure_group`, `spend_category`.
- **Model:** Spark MLlib logistic regression (80/20 split), AUC 0.843, accuracy 80.7%.
- **This dashboard** is the presentation layer. It reads exported pipeline outputs from `results/`,
  the HBase load file `hbase/hbase_puts.txt`, and the dataset for the deep-dive charts.
""")
