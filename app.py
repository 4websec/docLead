import pandas as pd
import streamlit as st

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv("scored_physicians.csv")
    df['license_states'] = df['license_states'].astype(str)
    df['locum_keywords'] = df['locum_keywords'].astype(str)
    df['license_states_list'] = df['license_states'].fillna('').apply(
        lambda x: [s.strip() for s in x.split(',') if s.strip()]
    )
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.title("🔍 Recruiter Filters")

with st.sidebar.expander("🎯 License State Filter", expanded=False):
    all_states = sorted(set(state for sublist in df['license_states_list'] for state in sublist))
    selected_states = st.multiselect(
        "Select state(s) licensed in:",
        options=all_states,
        default=all_states,
        key="license_state_filter"
    )
    df = df[df['license_states_list'].apply(lambda states: any(s in selected_states for s in states))]

# Additional filters
with st.sidebar.expander("⚙️ Advanced Filters", expanded=False):
    active_only = st.checkbox("Show Active Only", True)
    multi_state_only = st.checkbox("Show Multi-State Licensed Only")
    locum_only = st.checkbox("Show Locum Candidates Only")
    min_score = st.slider("Minimum Recruiter Score", 0, 100, 20)

if active_only:
    df = df[df['status'] == 'ACTIVE']
if multi_state_only:
    df = df[df['multi_state_licensed'] == True]
if locum_only:
    df = df[df['locum_candidate_flag'] == True]
df = df[df['recruiter_priority_score'] >= min_score]

# --- Header ---
st.title("🏥 Physician Lead Platform")
st.caption("Curated and scored for recruiter targeting")

st.markdown("""
<style>
    .big-font { font-size: 18px !important; font-weight: bold; }
    .stDataFrame thead tr th { background-color: #f4f4f4; }
    .metric-box { background: #fafafa; padding: 15px; border-radius: 10px; border: 1px solid #eaeaea; }
</style>
""", unsafe_allow_html=True)

# --- Summary Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Results", len(df))
col2.metric("🌍 Multi-State Licensed", df['multi_state_licensed'].sum())
col3.metric("🩺 Locum Candidates", df['locum_candidate_flag'].sum())

# --- Table Display ---
st.markdown("### 📋 Physician Leads")

def color_score(val):
    if val >= 80: return 'background-color: #c8e6c9'
    elif val >= 50: return 'background-color: #fff9c4'
    else: return 'background-color: #ffcdd2'

styled_df = df.style.applymap(color_score, subset=["recruiter_priority_score"])
st.dataframe(styled_df, use_container_width=True, hide_index=True)

# --- Download ---
st.markdown("### 📥 Download")
col_csv, col_pdf = st.columns(2)
with col_csv:
    st.download_button(
        label="⬇️ Download CSV",
        data=df.to_csv(index=False),
        file_name="filtered_physicians.csv",
        mime="text/csv"
    )
with col_pdf:
    st.markdown("_PDF export coming soon..._")

# --- Footer ---
st.markdown("---")
st.markdown(
    "🔧 Built with ❤️ for recruiter optimization. Contact [Landon Mayo](mailto:landonmayo722@gmail.com) for enterprise access."
)
