import mysql.connector

from config import Config


# 파이썬으로 mysql에 접속할 수 있는 함수.
def get_connection() :
    connection = mysql.connector.connect(
        host = Config.HOST,
        database = Config.DATABASE,
        user = Config.DB_USER,
        password = Config.PASSWORD
    )
    return connection

