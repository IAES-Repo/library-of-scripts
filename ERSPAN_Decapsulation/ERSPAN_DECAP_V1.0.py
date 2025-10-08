"""
ERSPAN Decapsulation Script v1.0
Listens for ERSPAN packets on a specified interface, decapsulates them,
and forwards the inner packets to a TAP device.

Author: Jordan Lanham
Date: 2025-10-08
"""

import os
import scapy.all as scapy

INTERFACE = "interface_name"  # Replace with your network interface
OUTPUT_TAP = "tap_name"  # Replace with your output TAP device name
ERSPAN_VER = 2  # ERSPAN version (1 or 2)

def create_tap_device(tap_name):
    if not os.path.exists(f"/dev/net/tun"):
        raise RuntimeError("TUN/TAP device not available")
    
    os.system(f"ip tuntap add dev {tap_name} mode tap")
    os.system(f"ip link set {tap_name} up")
    os.system(f"ip addr add 192.168.1.1/24 dev {tap_name}")
    print(f"TAP device {tap_name} created and configured.")

def packet_decap(packet):
    if packet.haslayer(scapy.ERSPAN):
        inner_packet = packet[scapy.ERSPAN].payload
        return inner_packet
    return None

def packet_callback(packet):
    decapped_packet = packet_decap(packet)
    if decapped_packet:
        scapy.sendp(decapped_packet, iface=OUTPUT_TAP, verbose=False)
        print(f"Forwarded packet: {decapped_packet.summary()}")
    else:
        print("No ERSPAN layer found, packet ignored.")
        return
    
def main():
    create_tap_device(OUTPUT_TAP)
    print(f"Listening on {INTERFACE} for ERSPAN packets...")
    scapy.sniff(iface=INTERFACE, prn=packet_callback, store=0)

if __name__ == "__main__":
    main()