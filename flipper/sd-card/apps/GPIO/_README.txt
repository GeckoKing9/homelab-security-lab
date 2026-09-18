==============================
 GPIO / WiFi / HARDWARE
==============================
OPTIONAL folder - needs the WiFi board on top.
Everything else on the Flipper works without it.

Two jobs live here: the WiFi Marauder (your
ESP32 board) and hardware hacking with the
Flipper's top pins.

--- WiFi MARAUDER (board attached) ---
Apps > GPIO > [ESP32] WiFi Marauder
- Scan ........ list WiFi networks
- Deauth ...... kick devices off YOUR network
- Sniff / PMKID / Handshake = capture to crack
- Evil Portal . fake login page on your AP
- Beacon spam . flood fake network names
Captures (.pcap) -> Pi (hcxpcapngtool) ->
crack on the RTX 4080 (hashcat -m 22000).
ESP Flasher app updates the board, no PC needed.
NOTE: this board is 2.4GHz only, no Bluetooth.

--- HARDWARE HACKING (needs jumper wires) ---
- USB-UART Bridge (GPIO menu) + UART Terminal:
  wire GND / TX / RX to a router's console pins,
  watch it boot - often drops to a root shell.
- SPI Mem Manager (+ SOIC8 clip): read the
  firmware off a flash chip -> analyze on the Pi.
- I2C Scanner: find chips on a circuit board.

RULE: your own hardware / networks or explicit
permission. Deauth = your network only.
No jamming.
