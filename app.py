import streamlit as st
import subprocess
import tempfile
import zipfile
import glob
import os
import pandas as pd
from datetime import datetime
import sys

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

                # derive date from the uploaded CSV's first Trade Time value
                try:
                    df_in = pd.read_csv(csv_path)
                    trade_vals = df_in["Trade Time"].dropna().unique()
                    if len(trade_vals) > 0:
                        first_trade = trade_vals[0]
                        if isinstance(first_trade, str):
                            date_str = first_trade.split(" ")[0]
                        else:
                            date_str = str(first_trade).split(" ")[0]
                    else:
                        date_str = datetime.now().strftime("%d-%m-%Y")
                except Exception:
                    date_str = datetime.now().strftime("%d-%m-%Y")

                zip_name = f"OrderSlips_{date_str}.zip"

                with zipfile.ZipFile(zip_name, "w") as z:
                    for pdf in pdfs:
                        z.write(pdf)

                consolidated_pdf = next(
                    (pdf for pdf in pdfs if pdf.startswith("Consolidated_OrderSlips_")),
                    None,
                )

                st.success(f"{len(pdfs)} PDFs generated, including a consolidated PDF.")

                with open(zip_name, "rb") as f:
                    st.download_button(
                        "Download ZIP",
                        data=f,
                        file_name=zip_name,
                        mime="application/zip"
                    )

                if consolidated_pdf is not None:
                    with open(consolidated_pdf, "rb") as f:
                        st.download_button(
                            "Download Consolidated PDF",
                            data=f,
                            file_name=consolidated_pdf,
                            mime="application/pdf"
                        )
