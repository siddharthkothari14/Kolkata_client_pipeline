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


PAGE_WIDTH, PAGE_HEIGHT = A4
TABLE_LEFT_MARGIN = 40
TABLE_TOP_Y = 620
FOOTER_HEIGHT = 80

TABLE_STYLE = TableStyle([
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
])


def build_table(page_data):
    table = Table(page_data)
    table.setStyle(TABLE_STYLE)
    return table


def get_rows_for_page(rows, start_index, headers, available_width, available_height):
    max_rows = 0
    for end_index in range(start_index + 1, len(rows) + 1):
        page_data = [headers] + rows[start_index:end_index]
        table = build_table(page_data)
        _, table_height = table.wrap(available_width, available_height)
        if table_height > available_height:
            break
        max_rows = end_index - start_index

    return max_rows if max_rows > 0 else 1


def create_order_slip(pandas_df, name, client_name=None):
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

    available_width = PAGE_WIDTH - 2 * TABLE_LEFT_MARGIN
    available_height = TABLE_TOP_Y - FOOTER_HEIGHT

    current_row = 0
    while current_row < len(rows):
        rows_this_page = get_rows_for_page(rows, current_row, headers, available_width, available_height)
        current_page_data = [headers] + rows[current_row:current_row + rows_this_page]

        if current_row > 0:
            c.showPage()
        add_page_content(c, current_page_data, name, timestamp, client_name=client_name)
        current_row += rows_this_page

    if len(rows) == 0:
        add_page_content(c, [headers], name, timestamp, client_name=client_name)

    c.save()
    return filename


def add_page_content(canvas_obj, page_data, name, timestamp, client_name=None):
    # Add header
    canvas_obj.drawString(50, 780, "ORDER SLIP")
    canvas_obj.drawString(50, 750, f"Date: {timestamp}")
    canvas_obj.drawString(50, 730, "To,")
    canvas_obj.drawString(50, 710, "Progressive Share Brokers Pvt Ltd")
    canvas_obj.drawString(50, 690, "Place: Kolkata")
    canvas_obj.drawString(50, 670, "Dear Sir/Madam,")
    canvas_obj.drawString(50, 650, "Kindly place the following Order in my/our Trading Account:-")

    # Create and draw table directly below the header to avoid a large gap
    table = build_table(page_data)
    available_width = PAGE_WIDTH - 2 * TABLE_LEFT_MARGIN
    _, table_height = table.wrap(available_width, TABLE_TOP_Y - FOOTER_HEIGHT)
    table.drawOn(canvas_obj, TABLE_LEFT_MARGIN, TABLE_TOP_Y - table_height)

    # Add footer
    canvas_obj.drawString(50, 80, "Thanking You,")
    canvas_obj.drawString(50, 60, "Signature: _________________")
    canvas_obj.drawString(50, 40, f"Client ID: {name}")
    canvas_obj.drawString(50, 20, f"Client Name: {client_name or name}")

special_users = {
    "K1N008", "K1N010", "K1B016", "K1S003", "K1S004",
    "K1R019", "K1S050", "K1S051", "K1B024", "K1I004",
    "K1V011", "K1M031", "K1S087", "K1S078", "K1S054",
    "K1N003" ,"K1S041" , "K1G022" , "K1M003" , "K1N013" ,
    "K1A050" ,  "K1S083" , "K1S072" , "K1S086" , "K1R024",
    "K1J013" , "K1J014" , "K1M033" , "K1R036" , "K1K030" ,
    "K1O001" , "K1S088" , "K1S056"
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

        client_name = None
        if "ClientName" in user_df.columns:
            client_name_values = user_df["ClientName"].dropna()
            if len(client_name_values) > 0:
                client_name = str(client_name_values.iloc[0])

        created_file = create_order_slip(final_final_user_df, user, client_name=client_name)
        generated_files.append(created_file)

if generated_files:
    consolidated_filename = f"Consolidated_OrderSlips_{date}.pdf"
    merge_pdf_files(generated_files, consolidated_filename)
