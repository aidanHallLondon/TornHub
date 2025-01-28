from bs4 import BeautifulSoup
from tabulate import tabulate

def generateStyledTable(data, headers, colalign):
    # generate html table
    table_html_str = tabulate(
        data, headers=headers, colalign=("right",), tablefmt="html"
    )
    soup = BeautifulSoup(table_html_str, "html.parser")

    for table in soup.find_all("table"):
        table["style"] = (
            "border-collapse: collapse; border: none;table-layout: fixed; width:95%;"
        )

    rows = soup.find_all("tr")
    for i, row in enumerate(rows):  # Add zebra stripes
        if i % 2 == 0:
            row["style"] = "background-color: #e0e0e0;"

    # Set column widths
    num_cols = len(headers)  # Assuming headers represent the number of columns
    col_width_percent = 100 / num_cols
    for row in rows:
        for cell in row.find_all("th"):
            cell["Style"] = (
                f" text-align: center; border:none; border-right:1px dotted #b0b0b0; font-size:smaller"
            )
        for cell in row.find_all("td"):
            cell["style"] = f"border:none;"

    # Get the modified HTML
    # return str(soup.prettify(formatter="minimal")).replace("\n","")
    html_str = str(soup.prettify(formatter="minimal"))  # .replace("\n", "")
    # Remove whitespace around numbers
    # html_str = re.sub(r"\s*(<|>)\s*", r"\1", html_str)
    return html_str