from app.utils.database import engine
from sqlalchemy import text

with engine.connect() as c:
    rows = c.execute(text("SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME='RESULT_TABLES'")).fetchall()
    print("RESULT_TABLES 真实列名:", [r[0] for r in rows])
    rows2 = c.execute(text("SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME='INDICATORS'")).fetchall()
    print("INDICATORS 真实列名:", [r[0] for r in rows2])
    rows3 = c.execute(text("SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME='JOB_RUNS'")).fetchall()
    print("JOB_RUNS 真实列名:", [r[0] for r in rows3])
