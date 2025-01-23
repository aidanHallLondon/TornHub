import sqlite3
from Torn.manageDB import initDB, updateDB, DB_CONNECTPATH
from tabulate import tabulate


def main():
    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    initDB(conn, cursor)  # creates the database structure if not already done
    conn.commit()
    updateDB(conn, cursor)  # updates the data using the API
    conn.commit()

    print("\n\n")
    cursor.execute("""PRAGMA integrity_check;""")
    print(
        tabulate(
            cursor.fetchall(),
            headers=[desc[0] for desc in cursor.description],
            tablefmt="simple",
        )
    )
    print("\n\foreign_key_check (empty is good)")
    cursor.execute("""PRAGMA foreign_key_check;""")
    print(
        tabulate(
            cursor.fetchall(),
            headers=[desc[0] for desc in cursor.description],
            tablefmt="simple",
        )
    )

    conn.commit()
    conn.close()

main()