import time 
from scapy.all import ( 
    Ether, 
    IP, 
    GRE, 
    rdpcap, 
    sniff, 
    wrpcap, 
    UDP, 
    TCP, 
) 
from scapy.contrib.erspan import ERSPAN_II 
  
  
INTERFACE = "eno8403" 
OUTPUT_PCAP_PREFIX = "decapsulated_erspan" 
PCAP_INTERVAL_SECONDS = 600  # 10 minutes 
  
  
current_pcap_filename = None 
start_time = None 
  
  
def get_pcap_filename(): 
    """ 
    Generates a unique PCAP filename based on the current timestamp. 
    """ 
    timestamp = time.strftime("%Y%m%d_%H%M%S") 
    return f"{OUTPUT_PCAP_PREFIX}_{timestamp}.pcap" 
  
  
def handle_packet(packet): 
    """ 
    This function is called for each captured packet. 
    It checks if the packet is an ERSPAN packet, decapsulates it, 
    and writes the decapsulated packet to the current output PCAP file. 
    """ 
    global current_pcap_filename, start_time 
  
    # Check if a new PCAP file needs to be created 
    if current_pcap_filename is None or time.time() - start_time >= PCAP_INTERVAL_SECONDS: 
        if current_pcap_filename: 
            print(f"Closing {current_pcap_filename}") 
        current_pcap_filename = get_pcap_filename() 
        start_time = time.time() 
        print(f"Opening new pcap: {current_pcap_filename}") 
  
    # Check if the packet has an ERSPAN_II layer 
    if ERSPAN_II in packet: 
        erspan = packet[ERSPAN_II] 
        # Decapsulate ERSPAN 
        inner_packet = erspan.payload 
  
        # Write the decapsulated packet to the output PCAP file 
        wrpcap(current_pcap_filename, inner_packet, append=True) 
  
        print( 
            f"Decapsulated and saved ERSPAN packet to {current_pcap_filename}" 
        ) 
  
  
def main(): 
    """ 
    Main function to start capturing packets on the specified interface. 
    """ 
    global current_pcap_filename, start_time 
    current_pcap_filename = get_pcap_filename() 
    start_time = time.time() 
    print(f"Listening on interface {INTERFACE} for ERSPAN packets...") 
    print(f"Saving to pcap: {current_pcap_filename}") 
    sniff(iface=INTERFACE, filter="proto gre", prn=handle_packet, store=0) 
  
  
if __name__ == "__main__": 
    main() 
