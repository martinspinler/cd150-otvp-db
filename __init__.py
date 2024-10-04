import os

from flask import Flask, request

import logging
logger = logging.getLogger("werkzeug")
logger.setLevel(logging.ERROR)


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

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        def parse_packet(data):
            number = sum([data[6 + i*2] * 10**i for i in range(3) if data[7 + i*2] == 0])
            verse =  sum([data[2 + i*2] * 10**i for i in range(2) if data[3 + i*2] == 0])
            variant = chr(data[14] - 10 + ord('A'))
            color = data[16] + 1

            return {
                "on": data[0] == 0,
                "number": None if data[11] != 0 else number,
                "verse": None if data[5] != 0 else verse,
                "variant": None if data[14] == 14 else variant,
                "color": None if data[16] == 4 else color,
            }

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
                pkt = []
        return 'OK\n'

    return app
