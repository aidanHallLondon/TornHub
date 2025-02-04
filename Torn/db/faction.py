import json
from Torn.api import cached_api_call
 
def getFaction(conn,cursor,params=None, cache_age_limit=3600, force=False):
    return cached_api_call(conn,cursor,"faction?selections=basic,currency,hof,stats", force=True )

def create_faction(conn,cursor, force=False):
    """
    Create the faction table in the database.
    """
    if force: cursor.execute("DROP TABLE IF EXISTS faction_history;")
    cursor.executescript(
        """CREATE TABLE IF NOT EXISTS faction_history (
        batch_date DATE PRIMARY KEY DEFAULT CURRENT_DATE,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        faction_id INTEGER NOT NULL,    
        faction_name TEXT NOT NULL,
        faction_tag TEXT NOT NULL,
        faction_tag_image TEXT NOT NULL,
        leader_id INTEGER NOT NULL,
        faction_state TEXT,
        co_leader_id INTEGER NOT NULL,
        respect INTEGER NOT NULL,
        days_old INTEGER NOT NULL,
        capacity INTEGER NOT NULL,
        members INTEGER NOT NULL,
        money INTEGER NOT NULL,
        points INTEGER NOT NULL,
        is_enlisted TEXT,
        rank_level INTEGER NOT NULL,
        rank_name TEXT NOT NULL,
        rank_division INTEGER NOT NULL,
        rank_position INTEGER NOT NULL,
        rank_wins INTEGER NOT NULL,
        best_chain INTEGER NOT NULL,
        hof_rank_rank INTEGER NOT NULL,
        hof_rank_value TEXT NOT NULL,
        hof_respect_rank INTEGER NOT NULL,
        hof_respect_value INTEGER NOT NULL,
        hof_chain_rank INTEGER NOT NULL,
        hof_chain_value INTEGER NOT NULL,
        medicalitemsused INTEGER NOT NULL,
        criminaloffences INTEGER NOT NULL,
        organisedcrimerespect INTEGER NOT NULL,
        organisedcrimemoney INTEGER NOT NULL,
        organisedcrimesuccess INTEGER NOT NULL,
        organisedcrimefail INTEGER NOT NULL,
        attackswon INTEGER NOT NULL,
        attackslost INTEGER NOT NULL,
        attackschain INTEGER NOT NULL,
        attacksleave INTEGER NOT NULL,
        attacksmug INTEGER NOT NULL,
        attackshosp INTEGER NOT NULL,
        bestchain INTEGER NOT NULL,
        busts INTEGER NOT NULL,
        revives INTEGER NOT NULL,
        jails INTEGER NOT NULL,
        hosps INTEGER NOT NULL,
        medicalitemrecovery INTEGER NOT NULL,
        medicalcooldownused INTEGER NOT NULL,
        gymtrains INTEGER NOT NULL,
        gymstrength INTEGER NOT NULL,
        gymspeed INTEGER NOT NULL,
        gymdefense INTEGER NOT NULL,
        gymdexterity INTEGER NOT NULL,
        candyused INTEGER NOT NULL,
        alcoholused INTEGER NOT NULL,
        energydrinkused INTEGER NOT NULL,
        drugsused INTEGER NOT NULL,
        drugoverdoses INTEGER NOT NULL,
        rehabs INTEGER NOT NULL,
        caymaninterest INTEGER NOT NULL,
        traveltimes INTEGER NOT NULL,
        traveltime INTEGER NOT NULL,
        hunting INTEGER NOT NULL,
        attacksdamagehits INTEGER NOT NULL,
        attacksdamage INTEGER NOT NULL,
        hosptimegiven INTEGER NOT NULL,
        hosptimereceived INTEGER NOT NULL,
        attacksdamaging INTEGER NOT NULL,
        attacksrunaway INTEGER NOT NULL,
        highestterritories INTEGER NOT NULL,
        territoryrespect INTEGER NOT NULL
   );
   
   CREATE INDEX IF NOT EXISTS faction_id_index  ON faction_history (batch_date);"""
    )
    cursor.executescript('''DROP VIEW IF EXISTS faction;
    CREATE VIEW faction AS
        SELECT * 
        FROM faction_history 
        ORDER BY batch_date DESC
        LIMIT 1;''')

def update_faction(conn,cursor, cache_age_limit=3600 * 12, force=False):
    data = getFaction(conn,cursor,
        params={"striptags": "false", "sort": "ASC"},
        cache_age_limit=cache_age_limit,
        force=force,
    )
    # print(json.dumps(data, indent=2))
    basic = data["basic"]
    hof = data["hof"]
    stats = data["stats"]
    if data:
        cursor.execute(
            """
            INSERT OR REPLACE INTO faction_history (
                batch_date, 
                faction_id, faction_name, faction_tag, faction_tag_image,
                leader_id, co_leader_id,
                respect, days_old, capacity, members,
                money, points,
                is_enlisted, 
                
                rank_level, rank_name, rank_division, 
                rank_position, rank_wins,
                best_chain,

                hof_rank_rank, hof_rank_value,
                hof_respect_rank, hof_respect_value,
                hof_chain_rank, hof_chain_value,

                medicalitemsused,
                criminaloffences, organisedcrimerespect, organisedcrimemoney,
                organisedcrimesuccess, organisedcrimefail, attackswon, attackslost,
                attackschain, attacksleave, attacksmug, attackshosp,
                bestchain, busts, revives, jails, hosps,
                medicalitemrecovery, medicalcooldownused, gymtrains,
                gymstrength, gymspeed, gymdefense, gymdexterity,
                candyused, alcoholused, energydrinkused, drugsused,
                drugoverdoses, rehabs, caymaninterest, traveltimes,
                traveltime, hunting, attacksdamagehits, attacksdamage,
                hosptimegiven, hosptimereceived, attacksdamaging,
                attacksrunaway, highestterritories, territoryrespect
            ) VALUES (
                CURRENT_DATE, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            ); """,
            (
                data["faction_id"],

                basic["name"],
                basic["tag"],
                basic["tag_image"],
                basic["leader_id"],
                basic["co-leader_id"],
                basic["respect"],
                basic["days_old"],
                basic["capacity"],
                basic["members"],
                data["money"],
                data["points"],
                basic["is_enlisted"],
                basic["rank"]["level"],
                basic["rank"]["name"],
                basic["rank"]["division"],
                basic["rank"]["position"],
                basic["rank"]["wins"],
                basic["best_chain"],
                hof["rank"]["rank"],
                hof["rank"]["value"],
                hof["respect"]["rank"],
                hof["respect"]["value"],
                hof["chain"]["rank"],
                hof["chain"]["value"],
                stats["medicalitemsused"],
                stats["criminaloffences"],
                stats["organisedcrimerespect"],
                stats["organisedcrimemoney"],
                stats["organisedcrimesuccess"],
                stats["organisedcrimefail"],
                stats["attackswon"],
                stats["attackslost"],
                stats["attackschain"],
                stats["attacksleave"],
                stats["attacksmug"],
                stats["attackshosp"],
                stats["bestchain"],
                stats["busts"],
                stats["revives"],
                stats["jails"],
                stats["hosps"],
                stats["medicalitemrecovery"],
                stats["medicalcooldownused"],
                stats["gymtrains"],
                stats["gymstrength"],
                stats["gymspeed"],
                stats["gymdefense"],
                stats["gymdexterity"],
                stats["candyused"],
                stats["alcoholused"],
                stats["energydrinkused"],
                stats["drugsused"],
                stats["drugoverdoses"],
                stats["rehabs"],
                stats["caymaninterest"],
                stats["traveltimes"],
                stats["traveltime"],
                stats["hunting"],
                stats["attacksdamagehits"],
                stats["attacksdamage"],
                stats["hosptimegiven"],
                stats["hosptimereceived"],
                stats["attacksdamaging"],
                stats["attacksrunaway"],
                stats["highestterritories"],
                stats["territoryrespect"],

            ),
        )

