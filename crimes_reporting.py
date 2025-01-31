import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.charts import init as charts_init
from Torn.reporting.crimes import crimeexp_rank_bump_plot
from Torn.reporting.oc import oc_item_requirements

def main():
    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    #
    # from Torn.reporting.crimes import crimeexp_rank_bump_plot
    charting_meta_data = charts_init(conn, cursor)
    user_colourList = charting_meta_data["colourList"]
    path = "reports/faction/crimes"
    out_filename = "bumps3"
    #
    crimeexp_rank_bump_plot(conn, cursor, user_colourList,limit_window=(75,100), path=path, out_filename=out_filename,show_image=True)
    #
    oc_item_requirements(conn,cursor,
                        template_file_path="templates/reports/oc/items_required.html",
                        title_str="Items Required",
                        path ="reports/faction/oc",
                        out_filename="items_required",)
    conn.close()


main()
