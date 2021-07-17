# -*- coding: utf-8 -*-
import psycopg2

def selectOperate(selectsql):
    conn = psycopg2.connect(database="t_db", user="guohao", password="Asbaize123", host="pgm-uf67v72l0gjcd3otso.pg.rds.aliyuncs.com", port="1921")
    cursor=conn.cursor()
    cursor.execute(selectsql)
    rows=cursor.fetchall()
    conn.close()
    return rows