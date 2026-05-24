from database.mysql_service import db

result = db.fetch_all("SELECT * FROM tai_xe")

print(result)
