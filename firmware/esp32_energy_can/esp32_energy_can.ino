// ESP32 energy can: the PC asks before releasing a skill; this board decides.
// Protocol (115200 baud, ASCII lines; see docs/esp32_energy.md):
//   PING               -> PONG <energy> <capacity>
//   REQ <id> <LABEL>   -> OK <id> <energy>  |  NO <id> <energy>
//   REFUND <id>        -> REFUNDED <id> <energy>  |  NO <id> <energy>
//   FILL               -> PONG <energy> <capacity>   (refill, for testing)
// The BOOT button (GPIO0) also refills the can.

#include <Arduino.h>

const int CAPACITY = 6;                  // energy units when full
const unsigned long RECHARGE_MS = 2000;  // +1 unit per interval
const int LED_PIN = 2;                   // on-board LED on most DevKit boards
const int BUTTON_PIN = 0;                // BOOT button, active low

struct Cost {
    const char *label;
    int cost;
};

// Unknown labels are denied. Cost 0 labels are always granted.
const Cost COSTS[] = {
    {"NORMAL_ATTACK", 0},
    {"JUMP", 0},
    {"ATTACK_SKILL", 1},
    {"DEFENSE_SKILL", 1},
    {"CONTROL_SKILL", 2},
    {"ULTIMATE", 3},
};

struct Ticket {
    long id;
    int cost;
    bool open;
};

const int TICKETS = 16;
Ticket tickets[TICKETS];
int nextTicket = 0;

int energy = CAPACITY;
unsigned long lastRecharge = 0;
unsigned long ledUntil = 0;
bool buttonWasDown = false;
char line[64];
size_t lineLength = 0;

int costOf(const char *label) {
    for (const Cost &c : COSTS) {
        if (strcmp(c.label, label) == 0) {
            return c.cost;
        }
    }
    return -1;
}

void reply(const char *kind, long id) {
    Serial.printf("%s %ld %d\n", kind, id, energy);
}

void pong() {
    Serial.printf("PONG %d %d\n", energy, CAPACITY);
}

void handleRequest(long id, const char *label) {
    int cost = costOf(label);
    if (cost < 0 || energy < cost) {
        reply("NO", id);
        return;
    }
    energy -= cost;
    tickets[nextTicket] = {id, cost, true};
    nextTicket = (nextTicket + 1) % TICKETS;
    ledUntil = millis() + 150;
    reply("OK", id);
}

void handleRefund(long id) {
    for (Ticket &t : tickets) {
        if (t.open && t.id == id) {
            t.open = false;
            energy = min(CAPACITY, energy + t.cost);
            reply("REFUNDED", id);
            return;
        }
    }
    reply("NO", id);
}

void handleLine(char *text) {
    char *command = strtok(text, " ");
    if (command == nullptr) {
        return;
    }
    if (strcmp(command, "PING") == 0) {
        pong();
    } else if (strcmp(command, "FILL") == 0) {
        energy = CAPACITY;
        pong();
    } else if (strcmp(command, "REQ") == 0) {
        char *id = strtok(nullptr, " ");
        char *label = strtok(nullptr, " ");
        if (id != nullptr && label != nullptr) {
            handleRequest(atol(id), label);
        }
    } else if (strcmp(command, "REFUND") == 0) {
        char *id = strtok(nullptr, " ");
        if (id != nullptr) {
            handleRefund(atol(id));
        }
    }
}

void readSerial() {
    while (Serial.available() > 0) {
        char c = Serial.read();
        if (c == '\r') {
            continue;
        }
        if (c == '\n') {
            line[lineLength] = '\0';
            handleLine(line);
            lineLength = 0;
        } else if (lineLength < sizeof(line) - 1) {
            line[lineLength++] = c;
        } else {
            lineLength = 0;  // overlong line: drop it
        }
    }
}

void recharge(unsigned long now) {
    if (energy >= CAPACITY) {
        lastRecharge = now;
        return;
    }
    while (now - lastRecharge >= RECHARGE_MS && energy < CAPACITY) {
        energy++;
        lastRecharge += RECHARGE_MS;
    }
}

void readButton() {
    bool down = digitalRead(BUTTON_PIN) == LOW;
    if (down && !buttonWasDown) {
        energy = CAPACITY;
    }
    buttonWasDown = down;
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    for (Ticket &t : tickets) {
        t = {0, 0, false};
    }
    lastRecharge = millis();
    Serial.printf("READY %d %d\n", energy, CAPACITY);
}

void loop() {
    unsigned long now = millis();
    readSerial();
    recharge(now);
    readButton();
    // Flash on grant; otherwise steady on while full.
    digitalWrite(LED_PIN, (long)(ledUntil - now) > 0 || energy >= CAPACITY ? HIGH : LOW);
    delay(1);
}
