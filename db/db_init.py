import pymysql
import os

def init_user_threads_table():
    db = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE'),
        charset='utf8mb4'
    )
    cursor = db.cursor()

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS user_threads (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
        thread_id VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL
    );
    """
    cursor.execute(create_table_sql)
    db.commit()
    cursor.close()
    db.close()