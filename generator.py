import os
import sys
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# Place the path of the file required to be used to generate the pdfs
csv_path = sys.argv[1]

df = pd.read_csv(csv_path)

user_list = df["ClientID"].unique().tolist()


def generate_unique_filename(name, timestamp):
    base_name = f"{name}_order_slip_{timestamp}.pdf"
    counter = 1

    while os.path.exists(base_name):
        base_name = f"order_slip_{timestamp}_{counter}.pdf"
        counter += 1

    return base_name


def create_order_slip(pandas_df, name):
    # NOTE: original script referenced an undefined `date` variable here
    # (date[0][0].split(" ")[0]). Using today's date instead, matching the
    # commented-out line that was already in the source.
    timestamp = datetime.now().strftime("%d%m%Y")
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


for user in user_list:
    if user == "K1N003" or user == "K1V011":
        user_df = df[df["ClientID"] == user].sort_values("Trade Time").reset_index(drop=True)
        user_df["SerialNumber"] = user_df.index + 1  # equivalent to row_number() over orderBy("Trade Time")

        grouped = (
            user_df.groupby(
                ["ClientID", "Symbol", "BuySell", "NorenOrderID", "Qty"],
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

        final_final_user_df["Price"] = final_final_user_df.apply(
            lambda row: max(row["collect_list(Price)"])
            if row["BuySell"] == "BUY"
            else min(row["collect_list(Price)"]),
            axis=1,
        )
        final_final_user_df = final_final_user_df.drop(columns=["collect_list(Price)"])

        create_order_slip(final_final_user_df, user)