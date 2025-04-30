
import pandas as pd
import streamlit as st

# --- Load Data ---
@st.cache_data(ttl=3600, max_entries=100)
def load_data():
    try:
        df = pd.read_csv("scored_physicians.csv")
    except FileNotFoundError:
        st.error("Error: The file 'scored_physicians.csv' was not found.")
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("Error: The file 'scored_physicians.csv' is empty or malformed.")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error loading data: {e}")
        st.stop()

    df['license_states'] = df['license_states'].astype(str)
    df['locum_keywords'] = df['locum_keywords'].astype(str)
    df['license_states_list'] = df['license_states'].fillna('').apply(
        lambda x: [s.strip() for s in x.split(',') if s.strip()]
    )
    return df

# Load full data for dropdown consistency
df_full = load_data()
df = df_full.copy()

# --- Sidebar UI ---
# Inject Bootstrap-inspired styling
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }

    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1em;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 1em;
    }

    .stTextArea > div > textarea {
        border-radius: 6px !important;
        padding: 10px !important;
        font-size: 0.95em !important;
    }

    .stButton > button {
        border-radius: 6px;
        padding: 8px 16px;
        background-color: #007bff;
        color: white;
        font-weight: 500;
        transition: 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #0056b3;
        color: white;
    }

    .stDownloadButton > button {
        background-color: #28a745;
        color: white;
        font-weight: bold;
        border-radius: 6px;
        padding: 10px 18px;
    }

    .stDownloadButton > button:hover {
        background-color: #218838;
        color: white;
    }

    .stDataFrame {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)
st.sidebar.title("🔍 Recruiter Filters")
dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode")

# Dark Mode Styling
if dark_mode:
    st.markdown("""
        <style>
        html, body, [class*="css"] {
            background-color: #1e1e1e !important;
            color: #ffffff !important;
        }
        .stTextInput > div > div > input,
        .stTextArea textarea {
            background-color: #2e2e2e !important;
            color: #ffffff !important;
        }
        .stDataFrame, .stExpander {
            background-color: #262626 !important;
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

# License State Filter
with st.sidebar.expander("🎯 License State Filter", expanded=False):
    all_states = sorted(set(state for sublist in df['license_states_list'] for state in sublist))
    selected_states = st.multiselect(
        "Select state(s) licensed in:",
        options=all_states,
        default=all_states
    )
    df = df[df['license_states_list'].explode().isin(selected_states).groupby(level=0).any()]

# Practice Area Filter (based on full dataset)
available_specialties = sorted(df_full['primary_specialty'].dropna().unique().tolist())
default_index = available_specialties.index("Emergency Medicine") if "Emergency Medicine" in available_specialties else 0
selected_specialty = st.sidebar.selectbox(
    "Filter by Practice Area",
    options=available_specialties,
    index=default_index
)
df = df[df['primary_specialty'] == selected_specialty]

# Advanced Filters
with st.sidebar.expander("⚙️ Advanced Filters", expanded=False):
    active_only = st.checkbox("Show Active Only", True)
    multi_state_only = st.checkbox("Show Multi-State Licensed Only")
    locum_only = st.checkbox("Show Locum Candidates Only")
    min_score = st.slider("Minimum Recruiter Score", 0, 100, 20)

if active_only:
    df = df[df['status'] == 'ACTIVE']
if multi_state_only:
    df = df[df['multi_state_licensed']]
if locum_only:
    df = df[df['locum_candidate_flag']]
df = df[df['recruiter_priority_score'] >= min_score]

# --- Session state for flagging ---
if "flagged" not in st.session_state:
    st.session_state.flagged = {}

# --- Header ---
st.title("🩺 MVP Solution for NorTek Medical")
st.markdown("*Developed by Landon Mayo*")
st.caption("Curated and scored for recruiter targeting")

# --- Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Results", len(df))
col2.metric("🌍 Multi-State Licensed", df['multi_state_licensed'].sum())
col3.metric("🩺 Locum Candidates", df['locum_candidate_flag'].sum())

# --- Profile Cards ---
st.markdown("### 📋 Physician Leads")

for row in df.itertuples(index=False):
    with st.expander(f"{row.full_name} | {row.primary_specialty} | Score: {row.recruiter_priority_score}"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**NPI**: {row.npi}")
            st.write(f"**Status**: {row.status}")
            st.write(f"**Email**: {getattr(row, 'Email', 'N/A')}")
            st.write(f"**Phone**: {row.phone}")
            st.write(f"**Practice Address**: {row.practice_address}")
            st.write(f"**License States**: {row.license_states}")
        with col2:
            current_note = st.session_state.flagged.get(row.npi, "")
            note = st.text_area("Flag this candidate:", value=current_note, key=f"note_{row.npi}")
            if note.strip():
                st.session_state.flagged[row.npi] = note.strip()

# --- Flagged Candidates ---
if st.session_state.flagged:
    st.markdown("### 🏷️ Flagged Candidates")
    flagged_data = df[df['npi'].isin(st.session_state.flagged.keys())].copy()
    flagged_data["flag_note"] = flagged_data["npi"].apply(lambda n: st.session_state.flagged.get(n, ""))
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
st.markdown("© 2024 Landon Mayo. All rights reserved.")
st.markdown("🔧 Built with ❤️ by the DocLeader Team. Contact [support@docleader.com](mailto:support@docleader.com) for access.")
