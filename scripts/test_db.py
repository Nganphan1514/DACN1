import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mysql_service import db

result = db.fetch_all("SELECT * FROM tai_xe")

print(result)
