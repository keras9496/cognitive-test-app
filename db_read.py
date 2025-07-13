import sqlite3

conn = sqlite3.connect("instance/results.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("테이블 목록:", tables)

for table in tables:
    cursor.execute(f"SELECT * FROM {table[0]} LIMIT 5;")
    print(f"{table[0]} 내용:", cursor.fetchall())

conn.close()