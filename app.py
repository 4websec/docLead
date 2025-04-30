import pandas as pd
import streamlit as st

# --- Load Data ---
@st.cache_data(ttl=3600, max_entries=100)
def load_data():
    try:
        df = pd.read_csv("scored_physicians.csv")
    except FileNotFoundError:
        st.error("Error: The file 'scored_physicians.csv' was not found. Please ensure the file exists in the correct location.")
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("Error: The file 'scored_physicians.csv' is empty or malformed. Please check the file content.")
        st.stop()
    except Exception as e:
        st.error("An unexpected error occurred while loading the file: {}".format(e))
        st.stop()
    df['license_states'] = df['license_states'].astype(str)
    df['locum_keywords'] = df['locum_keywords'].astype(str)
    df['license_states_list'] = df['license_states'].fillna('').apply(
        lambda x: [s.strip() for s in x.split(',') if s.strip()]
    )
    return df

# Load data at the start
df = load_data()

dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode")

# --- Initialize session state for flagged candidates ---
if "flagged" not in st.session_state:
    st.session_state.flagged = {}

# 🌙 Dark Mode Toggle
dark_mode = st.sidebar.toggle("🌙 Enable Dark Mode")

# Dark Mode CSS
if dark_mode:
    st.markdown("""
        <style>
        html, body, [class*="css"]  {
            background-color: #1e1e1e !important;
            color: #ffffff !important;
        }
        .stDataFrame { background-color: #262626 !important; }
        </style>
    """, unsafe_allow_html=True)

# 🎯 License State Filter
with st.sidebar.expander("🎯 License State Filter", expanded=False):
    all_states = sorted(set(state for sublist in df['license_states_list'] for state in sublist))
    selected_states = st.multiselect(
        "Select state(s) licensed in:",
        options=all_states,
        default=all_states,
        key="license_state_filter"
    )
    df = df[df['license_states_list'].explode().isin(selected_states).groupby(level=0).any()]

# 📚 Practice Area Filter
available_specialties = sorted(df['primary_specialty'].dropna().unique().tolist())
default_index = 0
if "Emergency Medicine" in available_specialties:
    default_index = available_specialties.index("Emergency Medicine")

selected_specialty = st.sidebar.selectbox(
    "Filter by Practice Area",
    options=available_specialties,
    index=default_index
)

with st.sidebar.expander("⚙️ Advanced Filters", expanded=False):
    active_only = st.checkbox("Show Active Only", True)
    multi_state_only = st.checkbox("Show Multi-State Licensed Only")
    locum_only = st.checkbox("Show Locum Candidates Only")
    min_score = st.slider("Minimum Recruiter Score", 0, 100, 20)
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

# --- Summary Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Results", len(df))
col2.metric("🌍 Multi-State Licensed", df['multi_state_licensed'].sum())
col3.metric("🩺 Locum Candidates", df['locum_candidate_flag'].sum())
# --- Table Display + Flag System ---
st.markdown("### 📋 Physician Leads")

for row in df.itertuples(index=False):
    with st.expander("{0}  |  {1}  |  Score: {2}".format(row.full_name, row.primary_specialty, row.recruiter_priority_score)):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("**NPI**: {}".format(row.npi))
            st.write("**Status**: {}".format(row.status))
            st.write("**Phone**: {}".format(row.phone))
            st.write("**Practice Address**: {}".format(row.practice_address))
            st.write("**License States**: {}".format(row.license_states))
        with col2:
            current_note = st.session_state.flagged.get(row.npi, "")
            note = st.text_area("Flag this candidate:", value=current_note, key="note_{}".format(row.npi))
            if note.strip():
                st.session_state.flagged[row.npi] = note.strip()
                st.session_state.flagged[row.npi] = note.strip()

# --- Flag Summary and Download ---
if st.session_state.flagged:
    st.markdown("### 🏷️ Flagged Candidates")
    flagged_data = df[df['npi'].isin(st.session_state.flagged.keys())].copy()
    flagged_data["flag_note"] = flagged_data["npi"].apply(lambda n: st.session_state.flagged.get(n, ""))
    # Get only columns that exist in the DataFrame
    display_columns = [col for col in ["full_name", "primary_specialty", "license_states", "recruiter_priority_score", "flag_note"] if col in flagged_data.columns]
    st.dataframe(flagged_data[display_columns])

    st.download_button(
        label="⬇️ Download Flagged CSV",
        data=flagged_data.to_csv(index=False).encode('utf-8'),
        file_name="flagged_physicians.csv",
        mime="text/csv"
    )

# --- Footer ---
st.markdown("---")
st.markdown("🔧 Built with ❤️ by the DocLeader Team. Contact [support@docleader.com](mailto:support@docleader.com) for access.")
