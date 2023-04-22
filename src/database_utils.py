import sqlite3


def get_cursor(club_url_name: str) -> sqlite3.Cursor:
    con = sqlite3.connect(f"databases/{club_url_name}.db")
    return con.cursor()
