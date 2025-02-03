import os
import shutil
import sqlite3
from Torn.browse import open_webapp
from Torn.charts import init as charts_init, load_user_colourList_for_charts
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import dumpResults, initDB
from Torn.reporting.all_tables import (
    move_template_file_with_subs,
    save_browsable_tables,
)
from Torn.reporting.build_menus import _menu_item_for_file, save_menus_as_html
from Torn.reporting.faction_revives import (
    list_revivers_to_html_file,
    revivers_share_donut,
    revives_pivot_to_html_file,
    revives_stackedarea_chart,
)
from Torn.reporting.crimes import crimeexp_rank_bump_plot
from Torn.reporting.oc import oc_item_requirements

imageExtension=".png"
conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
cursor = conn.cursor()
initDB(conn, cursor)  # creates the database structure if not already done
charting_meta_data = charts_init(conn, cursor)
user_colourList = charting_meta_data["colourList"]
conn.commit()

def main():
    print("Db------------")
    copy_assets_from_template_folder()
    db_menu = db_reporting()
    f_menu = faction_reporting()
    conn.close()
    save_menus_as_html(
        menus=[
            {
                "path": "faction",
                "menu": f_menu,
                "title": "Faction reports",
            },{
                "path": "db",
                "menu": db_menu,
                "title": "Database tables and views",
            },
        ],
        template_file="templates/_menu.html",
        out_filename="_menu.html",
    )

    open_webapp(quiet=True)

def db_reporting():
    db_menu = save_browsable_tables(conn, cursor)
    return db_menu


def copy_assets_from_template_folder():
    _copy_folder("templates/assets", "reports/assets")
    _copy_file("templates/db", "schema.html", "reports/db")
    move_template_file_with_subs(
        template_file_path="templates/_home.html",
        out_path="reports",
        out_filename="_home.html",
        substitutions=None,
    )
    move_template_file_with_subs(
        template_file_path="templates/index.html",
        out_path="reports",
        out_filename="index.html",
        substitutions=None,
    )


def _copy_file(source_path, file_name, destination_path):
    """Copies a folder and its contents to the destination, creating the target path if needed."""
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)
    try:
        shutil.copy(
            os.path.join(source_path, file_name),
            os.path.join(destination_path, file_name),
        )
    except OSError as e:
        print(f"Error copying file: {e}")


def _copy_folder(source, destination):
    """Copies a folder and its contents to the destination, creating the target path if needed."""
    if not os.path.exists(destination):
        os.makedirs(destination)
    try:
        shutil.copytree(source, destination, dirs_exist_ok=True)
        print(f"Successfully copied files from '{source}' to '{destination}'")
    except OSError as e:
        print(f"Error copying files: {e}")


def faction_reporting():
    fmenu = []
    fmenu = faction_revive_reporting(fmenu)
    fmenu = faction_crime_reporting(fmenu)
    fmenu = faction_oc_reporting(fmenu)
    return fmenu
    # menu.append(
    #     {
    #         "name": name,
    #         "icon": "•" if entity_type == "table" else "°",
    #         "type": entity_type,
    #         "row_count": row_count,
    #     },
    # )


def faction_oc_reporting(f_menu):
    path = "reports/faction/oc"
    template_path = "templates/reports/oc"
    #
    #
    m = oc_item_requirements(
        conn,
        cursor,
        template_file_path="templates/reports/oc/items_required.html",
        title_str="OC Items Required",
        path=path,
        out_filename="items_required.html",
    )
    f_menu.append(m)
    return f_menu


def faction_crime_reporting(f_menu):
    path = "reports/faction/crimes"
    out_filename = "bumps3"+imageExtension
    #
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 100),
        path=path,
        out_filename="Crime_experience_ranks_all"+imageExtension,
        show_image=False,
    )
    f_menu.append(_menu_item_for_file(path, "crime_exp_ranks_all", "Crime_experience_ranks_all"+imageExtension))

    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 25),
        path=path,
        out_filename="Crime_experience_ranks_top25"+imageExtension,
        show_image=False,
    )
    f_menu.append(_menu_item_for_file(path, "crime_exp_ranks_top-25", "Crime_experience_ranks_top25"+imageExtension))

    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 50),
        path=path,
        out_filename="Crime_experience_ranks_top50"+imageExtension,
        show_image=False,
    )
    f_menu.append(_menu_item_for_file(path, "crime_exp_ranks_top-50", "Crime_experience_ranks_top50"+imageExtension))
   
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(50, 100),
        path=path,
        out_filename="Crime_experience_ranks_bottom50"+imageExtension,
        show_image=False,
    )
    f_menu.append(_menu_item_for_file(path, "crime_exp_ranks_last-50", "Crime_experience_ranks_bottom50"+imageExtension))

    return f_menu

def faction_revive_reporting(f_menu):
    path = "reports/faction/revives"

    mi=revivers_share_donut(
        conn,
        cursor,
        title="Revivers total contributions",
        name="revives_contributors_total",
        period=None,
        path=path,
        out_filename="contributions_all"+imageExtension,
    )
    f_menu.append(mi)
    mi=None;

    mi=revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions over the last seven days",
        name="revives_contributors_7-days",
        period="-7 days",
        path=path,
        out_filename="contributions_7days"+imageExtension,
    )
    f_menu.append(mi)
    mi=None;

    mi=revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions over the last 30 days",        
        name="revives_contributors_30-days",
        period="-30 days",
        path=path,
        out_filename="contributions_30days"+imageExtension,
    )
    f_menu.append(mi)
    mi=None;

    mi=revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions this month",
        name="revives_contributors_1-month",
        period="-1 month",
        path=path,
        out_filename="contributions_month"+imageExtension,
    )
    f_menu.append(mi)
    mi=None;

    mi=list_revivers_to_html_file(
        conn,
        cursor,
        template_file_path="templates/reports/revives/revivers_forum_list.html",
        path=path,
        title_str="Revivers",
        out_filename="revivers_forum_list.html",
    ) 
    mi["name"]="revives_revivers_list"
    f_menu.append(mi)
    mi=None;



    template_revives_pivot_to_html_file_path = "templates/reports/revives/pivot.html"
    path = "reports/faction/revives"

    mi=revives_pivot_to_html_file(
        conn,
        cursor,
        template_revives_pivot_to_html_file_path,
        name="revives_by_date",
        path=path,
        periodAlias="date",
        periodName="date",
        title_str="Revives pivot by date",
        image_title="Charts",
        image_list=[
            "revives_stacked_area_by_date.png",
            "revives_stacked_area_by_date_12weeks.png",
        ],
        out_filename="by_date.html",
    )
    f_menu.append(_menu_item_for_file(path, "revives_by_date", "by_date.html"))

    mi=revives_pivot_to_html_file(
        conn,
        cursor,
        template_revives_pivot_to_html_file_path,
        name="revives_by_week",
        path=path,
        periodAlias="week",
        periodName="week",
        title_str="Revives pivot by week",
        image_title="Charts",
        image_list=[
            "revives_stacked_area_by_week.png",
            "revives_stacked_area_by_week_12weeks.png",
        ],
        out_filename="by_week.html",
    )

    f_menu.append(_menu_item_for_file(path, "revives_by_week", "by_week.html"))

    mi=revives_stackedarea_chart(
        conn,
        cursor,
        "week",
        "week",
        title="Revivers contributions by week",
        path=path,
        filename="stacked_area_by_week",
    )
    f_menu.append(_menu_item_for_file(path, "revives_by_week_all", "stacked_area_by_week.png"))


    mi=revives_stackedarea_chart(
        conn,
        cursor,
        "date",
        "date",
        title="Revivers contributions by day",
        path=path,
        filename="stacked_area_by_date",
    )
    f_menu.append(_menu_item_for_file(path, "revives_by_date_all", "stacked_area_by_date.png"))

    mi=revives_stackedarea_chart(
        conn,
        cursor,
        "week",
        "week",
        title="Revivers contributions by week over 12 weeks",
        path=path,
        filename="stacked_area_by_week_12weeks",
        truncate_after=12,
    )
    f_menu.append(_menu_item_for_file(path, "revives_by_week_last-12-weeks", "stacked_area_by_week_12weeks.png"))


    mi=revives_stackedarea_chart(
        conn,
        cursor,
        "date",
        "date",
        title="Revivers contributions by day over 12 weeks",
        path=path,
        filename="stacked_area_by_date_12weeks",
        truncate_after=12 * 7,
    )
    f_menu.append(_menu_item_for_file(path, "revives_by_date_last-12-weeks", "stacked_area_by_date_12weeks.png"))
    
    return f_menu

main()
