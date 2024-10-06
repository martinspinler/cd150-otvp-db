import os

from flask import Flask, request

import sqlite3

import logging

logger = logging.getLogger("werkzeug")
logger.setLevel(logging.ERROR)



def getdb():
    dbcon = sqlite3.connect("ciselnik/ciselnik.db")
    return dbcon


def create_db():
    dbcon = getdb()
    cur = dbcon.cursor()

    sql = """CREATE TABLE songs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        poweron INTEGER,
        number INTEGER,
        verse INTEGER,
        variant INTEGER,
        color INTEGER)
       """

    try:
        cur.execute(sql)
    except:
        pass
    dbcon.commit()
    dbcon.close()



def parse_packet(data):
    number = sum([data[6 + i*2] * 10**i for i in range(3) if data[7 + i*2] == 0])
    verse =  sum([data[2 + i*2] * 10**i for i in range(2) if data[3 + i*2] == 0])
    variant = chr(data[14] - 10 + ord('A'))
    color = data[16] + 1

    return {
        "on": data[0] == 0,
        "number": None if data[7] != 0 else number,
        "verse": None if data[3] != 0 else verse,
        "variant": None if data[14] == 14 else variant,
        "color": None if data[16] == 4 else color,
    }

def insert_db_row(data):
    dbcon = getdb()
    cur = dbcon.cursor()
    items = []
    values = []
    #on, number, verse, variant, color = [data[i] for i in ["on", "number", "verse", "variant", "color"]]

    row = {i: str(data[i]) for i in ["number", "verse", "color"] if data[i] is not None}
    row['poweron'] = str(1 if data['on'] else 0)
    #row['variant'] = ord(data['variant'])

    for k, v in row.items():
        items.append(k)
        values.append(v)

    create_db()
    items = ",".join(items)
    values = ",".join(values)
    sql = f"INSERT INTO songs ({items}) VALUES ({values})"
    #on, number, verse, variant, color) VALUES ({
    print(sql)
    cur.execute(sql)
    dbcon.commit()
    dbcon.close()


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/hello')
    def hello():
        data = bytes.fromhex(request.query_string.decode())
        pkt = []
        for n in data:
            if n & 0xF0 == 0xB0:
                if pkt:
                    if 0:
                        print("Unfinished packet", pkt)
                pkt = []
            pkt += [(n >> 0) & 0xF, (n >> 4) & 0xF]
            if n & 0xF0 == 0x20:
                data = parse_packet(pkt)
                print(pkt, data)
                insert_db_row(data)
                pkt = []
        return 'OK\n'

    return app
