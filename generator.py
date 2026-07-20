import os
import sys
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

# Place the path of the file required to be used to generate the pdfs
csv_path = sys.argv[1]

df = pd.read_csv(csv_path)
# Safely extract the first Trade Time date (equivalent to
# df.select("Trade Time").distinct().collect()[0][0].split(" ")[0] in Spark)
trade_vals = df["Trade Time"].dropna().unique()
if len(trade_vals) > 0:
    first_trade = trade_vals[0]
    if isinstance(first_trade, str):
        date = first_trade.split(" ")[0]
    else:
        date = str(first_trade).split(" ")[0]
else:
    date = datetime.now().strftime("%d-%m-%Y")

user_list = df["ClientID"].unique().tolist()


def generate_unique_filename(name, timestamp):
    base_name = f"{name}_order_slip_{timestamp}.pdf"
    counter = 1

    while os.path.exists(base_name):
        base_name = f"order_slip_{timestamp}_{counter}.pdf"
        counter += 1

    return base_name


def merge_pdf_files(pdf_paths, output_path):
    if not pdf_paths:
        return None

    writer = PdfWriter()
    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            continue
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    return output_path


def create_order_slip(pandas_df, name):
    # NOTE: original script referenced an undefined `date` variable here
    # (date[0][0].split(" ")[0]). Using today's date instead, matching the
    # commented-out line that was already in the source.
    
    # use the first Trade Time date from the CSV for the filename
    timestamp = date

    filename = generate_unique_filename(name, timestamp)
    c = canvas.Canvas(filename, pagesize=A4)

    # Convert DataFrame to list once
    headers = pandas_df.columns.tolist()
    rows = pandas_df.values.tolist()

    # First page with 6 rows
    first_page_rows = min(6, len(rows))
    current_page_data = [headers] + rows[:first_page_rows]

    # Add header, table and footer for first page
    add_page_content(c, current_page_data, name, timestamp, 400)

    # Handle remaining rows on subsequent pages
    current_row = first_page_rows
    rows_per_page = 23

    while current_row < len(rows):
        c.showPage()
        remaining_rows = len(rows) - current_row
        rows_this_page = min(rows_per_page, remaining_rows)
        current_page_data = [headers] + rows[current_row:current_row + rows_this_page]

        # Add header, table and footer for each subsequent page
        add_page_content(c, current_page_data, name, timestamp, 50)
        current_row += rows_this_page

    c.save()
    return filename


def add_page_content(canvas_obj, page_data, name, timestamp, y_offset):
    # Add header
    canvas_obj.drawString(50, 780, "ORDER SLIP")
    canvas_obj.drawString(50, 750, f"Date: {timestamp}")
    canvas_obj.drawString(50, 730, "To,")
    canvas_obj.drawString(50, 710, "Progressive Share Brokers Pvt Ltd")
    canvas_obj.drawString(50, 690, "Place: Kolkata")
    canvas_obj.drawString(50, 670, "Dear Sir/Madam,")
    canvas_obj.drawString(50, 650, "Kindly place the following Order in my/our Trading Account:-")

    # Create and draw table
    table = Table(page_data)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))

    table.wrapOn(canvas_obj, 40, y_offset + 100)
    table.drawOn(canvas_obj, 40, y_offset + 100)

    # Add footer
    canvas_obj.drawString(50, 50, "Thanking You,")
    canvas_obj.drawString(50, 30, "Signature: _________________")
    canvas_obj.drawString(50, 10, f"Client Name: {name}")

special_users = {
    "K1N008", "K1N010", "K1B016", "K1S003", "K1S004",
    "K1R019", "K1S050", "K1S051", "K1B024", "K1I004",
    "K1V011", "K1M031", "K1S087", "K1S078", "K1S054",
    "K1N003" ,"K1S041" , "K1G022" , "K1M003" , "K1N013" ,
    "K1A050" ,  "K1S083" , "K1S072" , "K1S086" , "K1R024",
    "K1J013" , "K1J014" , "K1M033" , "K1R036" , "K1K030" ,
    "K1O001" , "K1S088"
}

generated_files = []

for user in user_list:
    if user in special_users:
        user_df = df[df["ClientID"] == user].sort_values("Trade Time").reset_index(drop=True)
        user_df["SerialNumber"] = user_df.index + 1  # equivalent to row_number() over orderBy("Trade Time")

        grouped = (
            user_df.groupby(
                ["ClientName","ClientID", "Symbol", "BuySell", "NorenOrderID", "Qty"],
                as_index=False,
            ).agg(
                **{
                    "max(SerialNumber)": ("SerialNumber", "max"),
                    "collect_list(Price)": ("Price", list),
                }
            )
        )

        final_final_user_df = (
            grouped.sort_values("max(SerialNumber)")
            .drop(columns=["max(SerialNumber)", "NorenOrderID"])
            .reset_index(drop=True)
        )

        final_final_user_df["ClientID"] = final_final_user_df["ClientID"].astype(str)

        final_final_user_df["Price"] = final_final_user_df.apply(
            lambda row: max(row["collect_list(Price)"])
            if row["BuySell"] == "BUY"
            else min(row["collect_list(Price)"]),
            axis=1,
        )
        final_final_user_df = final_final_user_df.drop(columns=["collect_list(Price)"])

        created_file = create_order_slip(final_final_user_df, user)
        generated_files.append(created_file)

if generated_files:
    consolidated_filename = f"Consolidated_OrderSlips_{date}.pdf"
    merge_pdf_files(generated_files, consolidated_filename)
