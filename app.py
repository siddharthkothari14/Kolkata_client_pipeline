import streamlit as st
import subprocess
import tempfile
import zipfile
import glob
import os
import pandas as pd

st.set_page_config(page_title="PDF Generator", page_icon="📄")

st.title("Order Slip PDF Generator")

uploaded_file = st.file_uploader(
    "Upload CSV",
    type=["csv"]
)

if uploaded_file is not None:

    if st.button("Generate PDFs"):

        # Save uploaded CSV temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getbuffer())
            csv_path = tmp.name

        # Remove old PDFs
        for pdf in glob.glob("*.pdf"):
            os.remove(pdf)

        with st.spinner("Generating PDFs..."):

            result = subprocess.run(
                    [sys.executable, "generator.py", csv_path],
                    capture_output=True,
                    text=True
                )

        if result.returncode != 0:

            st.error("Generation failed.")
            st.code(result.stderr)

        else:

            pdfs = glob.glob("*.pdf")

            if len(pdfs) == 0:
                st.warning("No PDFs were generated.")

            else:

                zip_name = "OrderSlips.zip"

                with zipfile.ZipFile(zip_name, "w") as z:

                    for pdf in pdfs:
                        z.write(pdf)

                st.success(f"{len(pdfs)} PDFs generated!")

                with open(zip_name, "rb") as f:

                    st.download_button(
                        "Download ZIP",
                        data=f,
                        file_name="OrderSlips.zip",
                        mime="application/zip"
                    )
