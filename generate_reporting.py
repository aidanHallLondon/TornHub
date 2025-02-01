import sqlite3
from Torn.charts import init as charts_init, load_user_colourList_for_charts
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import dumpResults, initDB
from Torn.reporting.all_tables import move_template_file_with_subs, save_browsable_tables
from Torn.reporting.faction_revives import (
    list_revivers_to_html_file,
    revivers_share_donut,
    revives_pivot_to_html_file,
    revives_stackedarea_chart,
)
from Torn.reporting.crimes import crimeexp_rank_bump_plot
from Torn.reporting.oc import oc_item_requirements

conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
cursor = conn.cursor()
initDB(conn, cursor)  # creates the database structure if not already done
charting_meta_data = charts_init(conn, cursor)
user_colourList = charting_meta_data["colourList"]
conn.commit()


def main():
    print("Db------------")
    db_reporting()
    faction_revive_reporting()
    faction_crime_reporting()
    faction_oc_reporting()
    conn.close()

def db_reporting():
    save_browsable_tables(conn,cursor)
    move_template_file_with_subs( template_file_path="templates/db/_home.html",
        out_path= "reports/db",
        out_filename ="_home.html",
        substitutions=None)
    move_template_file_with_subs( template_file_path="templates/db/index.html",
        out_path= "reports/db",
        out_filename ="index.html",
        substitutions=None)                
           
def faction_oc_reporting():
    path = "reports/faction/oc"
    template_path="templates/reports/oc"
    #
   #
    oc_item_requirements(conn,cursor,
                        template_file_path="templates/reports/oc/items_required.html",
                        title_str="Items Required",
                        path =path,
                        out_filename="items_required.html",)


def faction_crime_reporting():
    path = "reports/faction/crimes"
    out_filename = "bumps3"
    #
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 100),
        path=path,
        out_filename="Crime_experience_ranks_all",
        show_image=False,
    )
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 25),
        path=path,
        out_filename="Crime_experience_ranks_top25",
        show_image=False,
    )
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 50),
        path=path,
        out_filename="Crime_experience_ranks_top50",
        show_image=False,
    )
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=( 50,100),
        path=path,
        out_filename="Crime_experience_ranks_bottom50",
        show_image=False,
    )


def faction_revive_reporting():
    path = "reports/faction/revives"

    revivers_share_donut(
        conn,
        cursor,
        title="Revivers total contributions",
        period=None,
        path=path,
        out_filename="contributions_all",
    )
    revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions over the last seven days",
        period="-7 days",
        path=path,
        out_filename="contributions_7days",
    )
    revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions over the last 30 days",
        period="-30 days",
        path=path,
        out_filename="contributions_30days",
    )
    revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions this month",
        period="-1 month",
        path=path,
        out_filename="contributions_month",
    )

    list_revivers_to_html_file(
        conn,
        cursor,
        template_file_path="templates/reports/revives/revivers_forum_list.html",
        path=path,
        title_str="Revivers",
        out_filename="revivers_forum_list.html",
    )

    template_revives_pivot_to_html_file_path = "templates/reports/revives/pivot.html"
    path = "reports/faction/revives"

    revives_pivot_to_html_file(
        conn,
        cursor,
        template_revives_pivot_to_html_file_path,
        path=path,
        periodAlias="date",
        periodName="date",
        title_str="Revives pivot by date",
        image_title="Charts",
        image_list=[
            "faction_revives_stacked_area_by_date.png",
            "faction_revives_stacked_area_by_date_12weeks.png",
        ],
        out_filename="by_date.html",
    )

    revives_pivot_to_html_file(
        conn,
        cursor,
        template_revives_pivot_to_html_file_path,
        path,
        periodAlias="week",
        periodName="week",
        title_str="Revives pivot by week",
        image_title="Charts",
        image_list=[
            "faction_revives_stacked_area_by_week.png",
            "faction_revives_stacked_area_by_week_12weeks.png",
        ],
        out_filename="by_week.html",
    )
    # pivot_to_stacked_area_chart(
    revives_stackedarea_chart(
        conn,
        cursor,
        "week",
        "week",
        title="Revivers contributions by week",
        path=path,
        filename="stacked_area_by_week",
    )
    revives_stackedarea_chart(
        conn,
        cursor,
        "date",
        "date",
        title="Revivers contributions by day",
        path=path,
        filename="stacked_area_by_date",
    )
    revives_stackedarea_chart(
        conn,
        cursor,
        "week",
        "week",
        title="Revivers contributions by week over 12 weeks",
        path=path,
        filename="stacked_area_by_week_12weeks",
        truncate_after=12,
    )
    revives_stackedarea_chart(
        conn,
        cursor,
        "date",
        "date",
        title="Revivers contributions by day over 12 weeks",
        path=path,
        filename="stacked_area_by_date_12weeks",
        truncate_after=12 * 7,
    )


main()
