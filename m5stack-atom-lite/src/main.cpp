#include <M5Atom.h>
#include <WiFi.h>
#include <WiFiMulti.h>

// secrets.h file must contains:
//static const char *wifi_ssid     = "";
//static const char *wifi_password = "";
//static const char *target_server_addr = "192.168.0.1";
//static const uint16_t target_server_port = 5000;

#include "secrets.h"


static uint8_t buffer[32];
static uint8_t buffer_pos = 0;

WiFiMulti WiFiMulti;


void setup()
{
    M5.begin(true, false, true);
    WiFiMulti.addAP(wifi_ssid, wifi_password);
    Serial2.begin(1200, SERIAL_8N1, 22, 19);
    while (WiFiMulti.run() != WL_CONNECTED) {
        delay(500);
        M5.dis.fillpix(0xff0000);
        delay(500);
        M5.dis.fillpix(0x000000);
    }
    delay(500);
    buffer_pos = 0;
}

int send_buffer(uint8_t *buffer, uint8_t buffer_pos, int retries)
{

    static const char *request_prefix = "GET /dpush?";

    static char req[128];

    int maxloops = 0;

    WiFiClient client;

    if (!client.connect(target_server_addr, target_server_port)) {
        return retries - 1;
    }

    sprintf(req, "%s", request_prefix);
    for (int i = 0; i < buffer_pos; i++) {
        sprintf(req + strlen(request_prefix) + i*2, "%02X", buffer[i]);
    }
    sprintf(req + strlen(req), " HTTP/1.1\n\n");

    client.print(req);

    while (!client.available() && maxloops < 2000) {
        maxloops++;
        delay(1);
    }

    client.stop();
    return 0;
}

void loop()
{
    uint8_t c;
    uint8_t n;

    if (Serial2.available() > 0) {
        c = Serial2.read();
        /*if (c & 0xF0 == 0xB0) {
            bufffer_pos = 0;
        }*/
        if (buffer_pos >= 32)
            buffer_pos = 0;

        buffer[buffer_pos] = c;
        buffer_pos += 1;

        if (c & 0xF0 == 0x20) {
            n = 3;
            do {
                n = send_buffer(buffer, buffer_pos, n);
            } while (n > 0);
            buffer_pos = 0;
        }
    }
}
