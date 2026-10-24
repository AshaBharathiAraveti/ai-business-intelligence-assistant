
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="RSG AI Business Intelligence",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Mini AI Business Intelligence Assistant")
st.caption("Ask questions about your sales data in natural language.")

# Check API status
try:
    health = requests.get(f"{API_URL}/health", timeout=5)
    if health.ok:
        st.success("Backend API connected")
    else:
        st.warning("Backend API returned an error.")
except requests.RequestException:
    st.error("Backend API is unavailable. Start FastAPI on port 8000.")

st.divider()

# Summary metrics
st.subheader("Sales Overview")

try:
    response = requests.get(f"{API_URL}/analytics/revenue", timeout=10)
    response.raise_for_status()
    revenue_data = response.json()

    col1, col2 = st.columns(2)
    col1.metric(
        "Total Revenue",
        f"₹{revenue_data['total_revenue']:,.2f}",
    )
    col2.metric(
        "Valid Revenue Transactions",
        revenue_data["transaction_count"],
    )
except requests.RequestException:
    st.info("Start the backend to view sales metrics.")

st.divider()

st.subheader("Ask Your Business Question")

examples = [
    "What is our total revenue?",
    "Which product generated the highest revenue?",
    "Which region has the highest revenue?",
    "Show monthly revenue",
    "Are there any data quality issues?",
]

selected_question = st.selectbox(
    "Choose an example or type your own question below:",
    ["Choose an example..."] + examples,
)

question = st.text_input(
    "Your question",
    value="" if selected_question == "Choose an example..." else selected_question,
    placeholder="e.g. Which product generated the highest revenue?",
)

if st.button("Analyze", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing your sales data..."):
            try:
                response = requests.post(
                    f"{API_URL}/ask",
                    json={"question": question},
                    timeout=60,
                )

                if response.ok:
                    result = response.json()
                    st.subheader("Analysis Result")
                    st.write(f"**Question:** {result['question']}")
                    st.write(f"**Detected intent:** `{result['intent']}`")
                    st.json(result["answer"])
                    st.caption(f"Source: {result['source']}")
                else:
                    try:
                        message = response.json().get(
                            "detail", "The request failed."
                        )
                    except ValueError:
                        message = "The server returned an unexpected response."
                    st.error(f"Could not analyze the question: {message}")

            except requests.RequestException as exc:
                st.error(f"Could not connect to the backend: {exc}")

st.divider()

st.subheader("Explore Detailed Analytics")

analytics_options = {
    "Revenue by Region": "/analytics/regions",
    "Monthly Revenue": "/analytics/monthly",
    "Top Revenue Product": "/analytics/top-product",
    "Data Quality Summary": "/analytics/data-quality",
}

choice = st.selectbox(
    "Select an analytics report",
    list(analytics_options.keys()),
)

if st.button("View Report"):
    try:
        response = requests.get(
            f"{API_URL}{analytics_options[choice]}",
            timeout=10,
        )
        response.raise_for_status()
        st.json(response.json())
    except requests.RequestException as exc:
        st.error(f"Unable to load report: {exc}")
