import os
import shutil
import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import get_last_updateDB_delta, initDB, updateDB
from Torn.reporting.user_activity import user_activity_json
from Torn.reporting.itemMarket import item_reporting
from Torn.reporting.reviver_bump import  reviver_ranks_json
from Torn.threads import run_background_threads_and_exit
from Torn.charts import close_all_figures, init as charts_init
from Torn.reporting.all_tables import (
    move_template_file_with_subs,
    save_browsable_tables,
)
from Torn.reporting.attacks import (
    attacks_incoming_overview,
    attacks_overview,
    incoming_attack_chart,
    outgoing_attack_chart,
)
from Torn.reporting.build_menus import _menu_item_for_file, save_menus_as_html
from Torn.reporting.faction import faction_data_page
from Torn.reporting.faction_revives import (
    list_revivers_to_html_file,
    revive_contract,
    revivers_share_donut,
    revives_pivot_to_html_file,
    revives_stackedarea_chart,
)
from Torn.reporting.crimes import crimeexp_rank_bump_plot
from Torn.reporting.oc import oc_item_requirements
from Torn.upload import upload_web

imageExtension = ".svg"
charting_meta_data = None
user_colourList = None

BACKGROUND_UPDATE_DUTY_CYCLE_SECONDS = 10
BACKGROUND_UPDATE_UPDATEDB_DUTY_CYCLE_SECONDS = 300


def main(fast=True):
    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    if not fast:
        initDB(conn, cursor)  # creates the database structure if not already done
    if not fast:
        updateDB(conn, cursor)
    #
    generate_reporting(conn, cursor)
    conn.commit()
    conn.close()
    upload_web()
    # 
    input("Press ENTER to run_background_threads")
    run_background_threads_and_exit(
        main_thread_func=main_thread_update,
        interval=BACKGROUND_UPDATE_DUTY_CYCLE_SECONDS,
    )


def main_thread_update():
    last_update = get_last_updateDB_delta()
    if (
        last_update is None
        or last_update > BACKGROUND_UPDATE_UPDATEDB_DUTY_CYCLE_SECONDS
    ):
        print("\n")
        conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        updateDB(conn, cursor)
        generate_reporting(conn, cursor)
        conn.commit()
        conn.close()
        print("\nMain thread: Update complete. Press ENTER to exit.")


def generate_reporting(conn, cursor):
    global user_colourList
    charting_meta_data = charts_init(conn, cursor)
    user_colourList = charting_meta_data["colourList"]
    # print("Db reports and schema")
    copy_assets_from_template_folder()
    db_menu = db_reporting(conn, cursor)
    f_menu = []
    f_menu = faction_reporting(conn, cursor, f_menu)
    f_menu = item_reporting(conn,cursor,f_menu)
    # 
    save_menus_as_html(
        menus=[
            {
                "path": "faction",
                "menu": f_menu,
                "title": "Faction reports",
            },
            {
                "path": "db",
                "menu": db_menu,
                "title": "Database tables and views",
            },
        ],
        template_file="templates/_menu.html",
        out_filename="_menu.html",
    )
    close_all_figures()


def attacks_reporting(conn, cursor, f_menu):
    f_menu = attacks_incoming_overview(conn, cursor, f_menu=f_menu)
    f_menu = attacks_overview(conn, cursor, f_menu=f_menu)
    f_menu = incoming_attack_chart(conn, cursor, f_menu=f_menu)
    f_menu = outgoing_attack_chart(conn, cursor, f_menu=f_menu)

    return f_menu


def db_reporting(conn, cursor):
    db_menu = save_browsable_tables(conn, cursor)
    return db_menu


def copy_assets_from_template_folder():
    _copy_folder("templates/assets", "reports/assets")
    _copy_file("templates/db", "schema.html", "reports/db")
    _copy_file("templates/reports", "_viewer.html", "reports/")
    _copy_file("templates/reports", "_viewer.html", "reports/")
    _copy_file("templates/reports/items/armory/items", "item_pricing.html", "reports/items/armory/items")
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
    if destination_path and not os.path.exists(destination_path):
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


def faction_reporting(conn, cursor, f_menu):
    # global user_colourList
    f_menu = attacks_reporting(conn, cursor, f_menu)
    f_menu.append(faction_data_page(conn, cursor))
    f_menu = faction_revive_reporting(conn, cursor, f_menu)
    f_menu = faction_crime_reporting(conn, cursor, f_menu)
    f_menu = faction_oc_reporting(conn, cursor, f_menu)
    _copy_file("templates/reports/user", "activity_e.html", "reports/user")
    user_activity_json(conn,cursor,path="reports/user",out_filename="activity_e")
    f_menu.append(
        _menu_item_for_file(
            "reports/user", "user_activity_90days", "activity_e.html" 
        )
    )
    return f_menu


def faction_oc_reporting(conn, cursor, f_menu):
    # global user_colourList
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


def faction_crime_reporting(conn, cursor, f_menu):
    global user_colourList
    #
    path = "reports/faction/crimes"
    out_filename = "bumps3" + imageExtension
    #
    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 100),
        path=path,
        out_filename="Crime_experience_ranks_all" ,
        show_image=False,
    )
    f_menu.append(
        _menu_item_for_file(
            path, "crime_exp_ranks_all", "Crime_experience_ranks_all" 
        )
    )

    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 25),
        path=path,
        out_filename="Crime_experience_ranks_top25" + imageExtension,
        show_image=False,
    )
    f_menu.append(
        _menu_item_for_file(
            path,
            "crime_exp_ranks_top-25",
            "Crime_experience_ranks_top25" + imageExtension,
        )
    )

    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(1, 50),
        path=path,
        out_filename="Crime_experience_ranks_top50" + imageExtension,
        show_image=False,
    )
    f_menu.append(
        _menu_item_for_file(
            path,
            "crime_exp_ranks_top-50",
            "Crime_experience_ranks_top50" + imageExtension,
        )
    )

    crimeexp_rank_bump_plot(
        conn,
        cursor,
        user_colourList,
        limit_window=(50, 100),
        path=path,
        out_filename="Crime_experience_ranks_bottom50" + imageExtension,
        show_image=False,
    )
    f_menu.append(
        _menu_item_for_file(
            path,
            "crime_exp_ranks_last-50",
            "Crime_experience_ranks_bottom50" + imageExtension,
        )
    )

    return f_menu


def faction_revive_reporting(conn, cursor, f_menu):
    _copy_file("templates/reports/faction/revives", "rank_count.html", "reports/faction/revives")
    _copy_file("templates/reports/faction/revives", "rank_skill.html", "reports/faction/revives")
 
    path = "reports/faction/revives"
    reviver_ranks_json(conn, cursor)

    f_menu.append(_menu_item_for_file(path, "revives_revivers_ranked", "rank_skill.html"))

    # f_menu.append(_menu_item_for_file(path, "revives_revivers_skill2", "rank_skill.html"))
    # http://localhost:8000/faction/revives/revivers_skill.svg

    path = "reports/faction/revives"
    mi = revivers_share_donut(
        conn,
        cursor,
        title="Revivers total contributions",
        name="revives_contributors_total",
        period=None,
        path=path,
        out_filename="contributions_all" ,
    )
    f_menu.append(mi)
    mi = None

    # mi = revivers_share_donut(
    #     conn,
    #     cursor,
    #     title="Revivers contributions over the last seven days",
    #     name="revives_contributors_7-days",
    #     period="-7 days",
    #     path=path,
    #     out_filename="contributions_7days" ,
    # )
    # f_menu.append(mi)
    # mi = None

    mi = revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions over the last 30 days",
        name="revives_contributors_30-days",
        period="-30 days",
        path=path,
        out_filename="contributions_30days" ,
    )
    f_menu.append(mi)
    mi = None

    mi = revivers_share_donut(
        conn,
        cursor,
        title="Revivers contributions this month",
        name="revives_contributors_1-month",
        period="-1 month",
        path=path,
        out_filename="contributions_month" ,
    )
    f_menu.append(mi)
    mi = None

    mi = list_revivers_to_html_file(
        conn,
        cursor,
        template_file_path="templates/reports/faction/revives/revivers_forum_list.html",
        path=path,
        title_str="Revivers",
        out_filename="revivers_forum_list.html",
    )
    mi["name"] = "revives_revivers_list"
    f_menu.append(mi)
    mi = None

    template_revives_pivot_to_html_file_path = "templates/reports/faction/revives/pivot.html"
    path = "reports/faction/revives"

    mi = revives_pivot_to_html_file(
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
            "revives_stacked_area_by_date.svg",
            "revives_stacked_area_by_date_12weeks.svg",
        ],
        out_filename="by_date.html",
    )
    f_menu.append(_menu_item_for_file(path, "revives_by_date", "by_date.html"))

    mi = revives_pivot_to_html_file(
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
            "revives_stacked_area_by_week.svg",
            "revives_stacked_area_by_week_12weeks.svg",
        ],
        out_filename="by_week.html",
    )

    f_menu.append(_menu_item_for_file(path, "revives_by_week", "by_week.html"))

    mi = revives_stackedarea_chart(
        conn,
        cursor,
        "week",
        "week",
        title="Revivers contributions by week",
        path=path,
        filename="stacked_area_by_week",
    )
    f_menu.append(
        _menu_item_for_file(path, "revives_by_week_all", "stacked_area_by_week.svg")
    )

    mi = revives_stackedarea_chart(
        conn,
        cursor,
        "date",
        "date",
        title="Revivers contributions by day",
        path=path,
        filename="stacked_area_by_date",
    )
    f_menu.append(
        _menu_item_for_file(path, "revives_by_date_all", "stacked_area_by_date.svg")
    )

    mi = revives_stackedarea_chart(
        conn,
        cursor,
        "week",
        "week",
        title="Revivers contributions by week over 12 weeks",
        path=path,
        filename="stacked_area_by_week_12weeks",
        truncate_after=12,
    )
    f_menu.append(
        _menu_item_for_file(
            path, "revives_by_week_last-12-weeks", "stacked_area_by_week_12weeks.svg"
        )
    )

    mi = revives_stackedarea_chart(
        conn,
        cursor,
        "date",
        "date",
        title="Revivers contributions by day over 12 weeks",
        path=path,
        filename="stacked_area_by_date_12weeks",
        truncate_after=12 * 7,
    )
    f_menu.append(
        _menu_item_for_file(
            path, "revives_by_date_last-12-weeks", "stacked_area_by_date_12weeks.svg"
        )
    )

    revive_contract(
        conn,
        cursor,
        revive_contract_id=1,
        template_file_path="templates/reports/faction/revives/contract.html",
        name="revives_contract_1",
        path=path,
        out_filename="revive_contract_1.html",
    )
    f_menu.append(
        _menu_item_for_file(
            path, "revives_contract_1", "revive_contract_1.html"
        )
    )
    revive_contract(
        conn,
        cursor,
        revive_contract_id = 2,
        template_file_path="templates/reports/faction/revives/contract.html",
        name="revives_contract_2",
        path=path,
        out_filename="revive_contract_2.html",
    )
    f_menu.append(
        _menu_item_for_file(
            path, "revives_contract_2", "revive_contract_2.html"
        )
    )
    return f_menu


main()
