import streamlit as st

import bioprocess

st.set_page_config(page_title="Bioprocess Phase Planner", layout="wide")
st.title("Bioprocess Phase Planner")
st.caption(f"Model {bioprocess.MODEL_VERSION} · your inputs never leave this computer")
st.info("Scaffold (M0). The model arrives in M1, the input pages in M2.")
