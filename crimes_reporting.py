import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.charts import init as charts_init
from Torn.reporting.crimes import crimeexp_rank_bump_plot

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
    conn.close()


main()
