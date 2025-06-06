import pandas as pd
import streamlit as st
import os
import shutil
from datetime import datetime

def backup_data():
    """Create backup of scored_physicians.csv before overwriting"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    src = "scored_physicians.csv"
    dst = f"backup/scored_physicians_{timestamp}.csv"
    
    # Create backup dir if it doesn't exist
    os.makedirs("backup", exist_ok=True)
    
    # Copy file
    shutil.copy2(src, dst)
    return dst

# --- Load Data ---
@st.cache_data(ttl=3600, max_entries=100)
def load_data():
    try:
        # Create backup first
        backup_file = backup_data()
        st.info(f"Created backup at: {backup_file}")
        
        # Now load the new data
        df = pd.read_csv("scored_physicians.csv")
        
        # Validate required columns
        required_columns = [
            'npi', 'full_name', 'primary_specialty', 'license_states',
            'multi_state_licensed', 'locum_candidate_flag', 'recruiter_priority_score'
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            st.stop()
            
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
        .dataframe {
            background-color: #262626 !important;
            color: #ffffff !important;
        }
        .dataframe th {
            background-color: #363636 !important;
            color: #ffffff !important;
        }
        .dataframe td {
            background-color: #262626 !important;
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

# Sidebar filters
st.sidebar.header('Filters')

# Simplified specialty filter
specialty_filter = st.sidebar.radio(
    'Doctor Type',
    options=['All Doctors', 'Emergency Room Doctors']
)

# Apply filters
def filter_data(df):
    filtered_df = df.copy()
    
    # Apply specialty filter
    if specialty_filter == 'Emergency Room Doctors':
        filtered_df = filtered_df[filtered_df['primary_specialty'].str.contains('Emergency', case=False, na=False)]
    
    return filtered_df

# Apply filters to dataframe
df = filter_data(df)

# License State Filter
with st.sidebar.expander("🎯 License State Filter", expanded=False):
    all_states = sorted(set(state for sublist in df['license_states_list'] for state in sublist))
    selected_states = st.multiselect(
        "Select state(s) licensed in:",
        options=all_states,
        default=all_states
    )
    df = df[df['license_states_list'].explode().isin(selected_states).groupby(level=0).any()]

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
st.title("🩺 DocHunter - Recruiter Intelligence Dashboard")
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
st.markdown("© 2025 Landon Mayo. All rights reserved.")
st.markdown("🔧 Built with ❤️ by Landon Mayo. Contact [support@dochunter.ai](mailto:support@dochunter.ai) for access.")

# Chat Widget
import streamlit.components.v1 as components

components.html("""
<script>
(function(d, w, c) {
    w.ChatraID = 'kTDcPP2zG6v5BekLG';
    var s = d.createElement('script');
    w[c] = w[c] || function() {
        (w[c].q = w[c].q || []).push(arguments);
    };
    s.async = true;
    s.src = 'https://call.chatra.io/chatra.js';
    if (d.head) d.head.appendChild(s);
})(document, window, 'Chatra');
</script>
""", height=100)
