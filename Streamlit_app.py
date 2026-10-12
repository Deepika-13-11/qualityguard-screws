
import streamlit as st
import pandas as pd
import subprocess
import sys
import tempfile
import os

st.set_page_config(page_title="QualityGuard Screws", page_icon="🔩")

st.title("🔩 QualityGuard Screws")
st.subheader("AI-Assisted Screw Quality Inspection")
st.write("Upload a CSV file containing screw measurement data.")

uploaded_file = st.file_uploader("Upload measurements (CSV)", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.write("### Uploaded measurements")
        st.dataframe(df)

        if st.button("Run Quality Inspection"):
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".csv", delete=False
            ) as f:
                f.write(uploaded_file.getvalue())
                csv_path = f.name

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "qualityguard_agent.py",
                        csv_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                st.write("### Inspection Results")
                if result.stdout:
                    st.code(result.stdout)

                if result.stderr:
                    st.text("Diagnostic output:")
                    st.code(result.stderr)

                if result.returncode != 0:
                    st.error("Inspection ended with an error.")
            except subprocess.TimeoutExpired:
                st.error("Inspection timed out. Try a smaller CSV.")
            finally:
                os.unlink(csv_path)

    except Exception as e:
        st.error(f"Could not read the CSV: {e}")
else:
    st.info("Upload a CSV file to begin inspection.")
