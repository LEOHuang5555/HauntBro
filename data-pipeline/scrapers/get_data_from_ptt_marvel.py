from sqlalchemy import create_engine, text

# 設定資料庫連線 URL
DATABASE_URL = "postgresql+psycopg2://hbadmin:dj3jkp2jmrkfmlkweq@localhost/hbrawdata"

# 創建引擎
engine = create_engine(DATABASE_URL)

# 測試連接
with engine.connect() as connection:
    result = connection.execute(text("SELECT version();"))
    for row in result:
        print(f"Connected to - {row[0]}")
