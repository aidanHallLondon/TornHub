import os
from Torn.reporting.reporting import move_template_file_with_subs

from datetime import datetime, timedelta


def faction_data_page(
    conn,
    cursor,
    template_file_path="templates/reports/faction/faction.html",
    path="reports/faction",
    out_filename="faction.html",
):  
    title_str = f"Faction data"
    table_title = f"Faction facts compared to one week ago"
    html=''
    cols =get_faction_columns()
    select_fields = ", ".join([col[0] for col in cols])
    # select two rows – the latest row and the row nearest to one week ago 
    cursor.execute(
        f"""
        SELECT batch_date,{select_fields} FROM (
		   SELECT * FROM (SELECT * FROM faction_history ORDER BY Batch_date DESC LIMIT 1)
			UNION ALL
			SELECT * FROM (
				SELECT * FROM faction_history
				WHERE Batch_date < (SELECT MAX(Batch_date) FROM faction_history
			) ORDER BY ABS(JULIANDAY((SELECT MAX(Batch_date) FROM faction_history)) - JULIANDAY(Batch_date) - 7 )
			LIMIT 1)
		);""")
    column_names = [description[0] for description in cursor.description]
    records=cursor.fetchall()
    latest_data = records[0]
    reference_data_1week = records[1]
    for i,datum in enumerate(latest_data):
        value=str(datum)
        col_type= cols[i-1][1]
        if i==0: # the first datum in the batch_date
            dateDiff= datum-reference_data_1week[0] 
            value = f"""{datum} <span class="ref positive">{dateDiff.days}</span>""" 
        else:
            if col_type=='MONEY' or col_type=='INTEGER':
                datum = datum if datum is not None else 0
                prefix="$" if col_type=='MONEY' else ""
                ref = reference_data_1week[i] if reference_data_1week[i] else 0
                delta = datum - ref
                sub_class=""
                if delta==0:
                    delta=''
                else: 
                    sub_class="negative" if delta<0 else "positive"
                    delta=f"""<span class="ref {sub_class}">{prefix}{delta:,}</span>"""
                value = f"""{prefix}{datum:,} {delta}""" if isinstance(datum, int) else str(datum)

        html+=f"""<div class="datum">
        <div class="label">{ column_names[i]}</div>
        <div class="value">{value}</div>
        </div>"""
    html=f'''<div class="data-grid">\n{html}\n</div>'''
    move_template_file_with_subs(
        template_file_path=template_file_path,
        out_path=path,
        out_filename=out_filename,
        substitutions={
            "page_title": title_str,
            "content_html": html,
            "sub_title": table_title,
        },
    )

    return {
        "name": "Faction_facts",
        "href": os.path.join("faction",out_filename),
        "icon": "•",
        "type": "file",
        "row_count": 1,
    }

def get_faction_columns():
    return  [
     ("faction_id", "INTEGER"),
    ("faction_name", "TEXT"),
    ("faction_tag", "TEXT"),
    ("faction_state", "TEXT"),
    # ("leader_id", "INTEGER"),
    # ("co_leader_id", "INTEGER"),
    ("respect", "INTEGER"),
    ("days_old", "INTEGER"),
    ("capacity", "INTEGER"),
    ("members", "INTEGER"),
    ("money", "MONEY"),
    ("points", "INTEGER"),
    ("is_enlisted", "TEXT"),
    ("rank_level", "INTEGER"),
    ("rank_name", "TEXT"),
    ("rank_division", "INTEGER"),
    ("rank_position", "INTEGER"),
    ("rank_wins", "INTEGER"),
    ("best_chain", "INTEGER"),
    ("hof_rank_rank", "INTEGER"),
    ("hof_rank_value", "TEXT"),
    ("hof_respect_rank", "INTEGER"),
    ("hof_respect_value", "INTEGER"),
    ("hof_chain_rank", "INTEGER"),
    ("hof_chain_value", "INTEGER"),
    ("medicalitemsused", "INTEGER"),
    ("criminaloffences", "INTEGER"),
    ("organisedcrimerespect", "INTEGER"),
    ("organisedcrimemoney", "INTEGER"),
    ("organisedcrimesuccess", "INTEGER"),
    ("organisedcrimefail", "INTEGER"),
    ("attackswon", "INTEGER"),
    ("attackslost", "INTEGER"),
    ("attackschain", "INTEGER"),
    ("attacksleave", "INTEGER"),
    ("attacksmug", "INTEGER"),
    ("attackshosp", "INTEGER"),
    ("bestchain", "INTEGER"),  
    ("busts", "INTEGER"),
    ("revives", "INTEGER"),
    ("jails", "INTEGER"),
    ("hosps", "INTEGER"),
    ("medicalitemrecovery", "INTEGER"),
    ("medicalcooldownused", "INTEGER"),
    ("gymtrains", "INTEGER"),
    ("gymstrength", "INTEGER"),
    ("gymspeed", "INTEGER"),
    ("gymdefense", "INTEGER"),
    ("gymdexterity", "INTEGER"),
    ("candyused", "INTEGER"),
    ("alcoholused", "INTEGER"),
    ("energydrinkused", "INTEGER"),
    ("drugsused", "INTEGER"),
    ("drugoverdoses", "INTEGER"),
    ("rehabs", "INTEGER"),
    ("caymaninterest", "INTEGER"),
    ("traveltimes", "INTEGER"),
    ("traveltime", "INTEGER"),
    ("hunting", "INTEGER"),
    ("attacksdamagehits", "INTEGER"),
    ("attacksdamage", "INTEGER"),
    ("hosptimegiven", "INTEGER"),
    ("hosptimereceived", "INTEGER"),
    ("attacksdamaging", "INTEGER"),
    ("attacksrunaway", "INTEGER"),
    ("highestterritories", "INTEGER"),
    ("territoryrespect", "INTEGER")
]