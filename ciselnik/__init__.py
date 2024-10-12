import os
from dataclasses import dataclass
from typing import Optional
import datetime
from dateutil import tz
import sqlite3
import logging

from flask import Flask, request, render_template


logger = logging.getLogger("werkzeug")
#logger.setLevel(logging.ERROR)

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

@dataclass
class Song:
    created: datetime.datetime
    poweron: bool
    number: int
    verse: int
    variant: int
    color: int
    flags: int = 0
    id: Optional[int] = None

    #def __repr__(self):
    #    return f"{self.number:> 3} {self.created}"

    def pass__init__(self, data, **kwargs):
        if not isinstance(data, list):
            pass
        utc_time = data[1]
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        utc = datetime.datetime.strptime(utc_time, TIME_FORMAT)
        utc = utc.replace(tzinfo=from_zone)
        local_time = utc.astimezone(to_zone)

        super().__init__(
            id=data[0],
            poweron=bool(data[2]),
            number=data[3],
            verse=data[4],
            variant=data[5],
            color=data[6],
            flags=data[7],
            stime=local_time,
            stime_utc=data[1],
            time_utc=utc,
        )

    @classmethod
    def from_dbdata(cls, data):
        stime_utc = data[1]
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        utc = datetime.datetime.strptime(stime_utc, TIME_FORMAT)
        local_time = utc.replace(tzinfo=from_zone).astimezone(to_zone)

        data=dict(
            id=data[0],
            created=utc,
            poweron=bool(data[2]),
            number=data[3],
            verse=data[4],
            variant=data[5],
            color=data[6],
            flags=data[7],
            #stime=local_time,
            #stime_utc=data[1]
        )
        return cls(**data)

    @property
    def created_local(self):
        to_zone = tz.tzlocal()
        from_zone = tz.tzutc()
        time = self.created.replace(tzinfo=from_zone)
        return time.astimezone(to_zone)


def getdb():
    dbcon = sqlite3.connect("ciselnik.db")
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
        color INTEGER,
        flags INTEGER)
       """

    try:
        cur.execute(sql)
    except:
        pass
    dbcon.commit()
    dbcon.close()



def parse_input(data):
    number = sum([data[6 + i*2] * 10**i for i in range(3) if data[7 + i*2] == 0])
    verse =  sum([data[2 + i*2] * 10**i for i in range(2) if data[3 + i*2] == 0])
    variant = chr(data[14] - 10 + ord('A'))
    color = data[16] + 1

    init = {
        "created": datetime.datetime.now(),
        "poweron": data[0] == 0,
        "number": None if data[7] != 0 else number,
        "verse": None if data[3] != 0 else verse,
        "variant": None if data[14] == 14 else variant,
        "color": None if data[16] == 4 else color,
    }
    return Song(**init)


def is_essential(dbcon, song):
    if not song.poweron:
        return False

    deltas = [dict(minutes=90), dict(seconds=1)]
    ts_start, ts_end = [
        (song.created - datetime.timedelta(**td))
            .astimezone(tz.tzutc())
            .strftime(TIME_FORMAT)
        for td in deltas
    ]
    sql = f'SELECT * from songs WHERE created > "{ts_start}" AND created < "{ts_end}" ORDER BY created DESC'
    cur = dbcon.cursor()
    ret = cur.execute(sql)
    songs = ret.fetchall()
    songs = [Song.from_dbdata(s) for s in songs]

    same_number = False
    for s in songs:
        if song.number == s.number:
            same_number = True

    if same_number:
        return False

    return True


def insert_db_row(song):
    dbcon = getdb()
    cur = dbcon.cursor()
    items = []
    values = []

    row = {i: str(getattr(song, i)) for i in ["number", "verse", "color"] if getattr(song, i) is not None}
    row['poweron'] = str(1 if song.poweron else 0)
    #row['variant'] = ord(data['variant'])

    for k, v in row.items():
        items.append(k)
        values.append(v)

    if is_essential(dbcon, song):
        song.flags |= 1
        items.append("flags")
        values.append("1")

    create_db()
    items = ",".join(items)
    values = ",".join(values)
    sql = f"INSERT INTO songs ({items}) VALUES ({values})"
    #print(sql)
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
                #print("Data:", pkt)
                song = parse_input(pkt)
                insert_db_row(song)
                print("Song:", song)

                pkt = []

        return 'OK\n'

    @app.route('/')
    def main():
        dbcon = getdb()
        cur = dbcon.cursor()
        sql = f"SELECT * from songs WHERE (flags & 1) = 1 ORDER BY created DESC "
        ret = cur.execute(sql)
        songs = ret.fetchall()
        songs = [Song.from_dbdata(s) for s in songs]

        return render_template('base.html', songs=songs)

    return app
