'''
PDF Parser v1.0

This script processes PDF reports, extracts structured data, and outputs CSV files.
Usage:
  - To watch a directory for new PDFs:
      python3 pdf_parser.py <directory>
  - To process a single PDF file:
      python3 pdf_parser.py --single <pdf_file>

Author: Jordan Lanham
Date: 2026-1-12
'''


import re
import csv
import sys
import os
import glob
import time
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader

REPORT_TITLE_PATTERN = r'(FM-Report-[\w-]+)\.pdf'
TIMESTAMP_PATTERN = r'(\d{8})(\d{6})-(\d+)'
IP_PATTERN = r'\d+\.\d+\.\d+\.\d+'
SNORT_ID_PATTERN = r'^\d+:\d+:\d+'
PROTOCOL_APP_PATTERN = r'^([\w\-/.]+(?:\s*\([\w\-/]+\))?)\s+([\d,]+(?:\.\d+)?)\s*$'
PROTOCOL_PACKETS_PATTERN = r'^([\w\-/.]+(?:\s*\([\w\-/]+\))?)\s+([\d,]+)\s*$'
IP_CONN_PATTERN = r'^([\d.]+)\s+([\d,]+)\s*$'
IP_BYTES_PATTERN = r'^([\d.]+)\s+([\d,]+(?:\.\d+)?)\s*$'
PROTOCOL_PATTERN = r'^[\w\-/.]+(?:\s*\([\w\-/]+\))?'
TRAILING_NUMS_PATTERN = r'\d+\s*$'

PROCESSED_FILES = set()
OUTPUT_DIR = './output'


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")


def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        return '\n'.join(pages)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def parse_metadata(text, filename):
    data = {}
    
    filename_match = re.search(REPORT_TITLE_PATTERN, filename)
    if filename_match:
        data['Report_Title'] = filename_match.group(1)
    
    timestamp_match = re.search(TIMESTAMP_PATTERN, filename)
    if timestamp_match:
        date_str, time_str, report_id = timestamp_match.groups()
        data['Report_Date'] = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        data['Report_Time'] = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        data['Report_ID'] = report_id
    
    data['Filename'] = filename
    return data


def extract_section(text, start_marker, end_marker):
    pattern = f'{re.escape(start_marker)}(.*?)(?={re.escape(end_marker)})'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None


def extract_app_usage_bytes(text):
    section = extract_section(text, 'Application Usage (bytes)', 'Application Usage (pkts)')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Protocol' in line and 'Traffic' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(PROTOCOL_APP_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Application Protocol', 'Traffic (KB)'], 'rows': rows} if rows else None


def extract_app_usage_packets(text):
    section = extract_section(text, 'Application Usage (pkts)', 'Web Applications')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Protocol' in line and 'Packets' in line and 'Total' in line:
            in_data = True
            continue
        if in_data and line and re.match(PROTOCOL_PATTERN, line):
            match = re.match(PROTOCOL_PACKETS_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
                break
    
    return {'headers': ['Application Protocol', 'Total Packets'], 'rows': rows} if rows else None


def extract_web_applications(text):
    section = extract_section(text, 'Web Applications', 'Operating Systems')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Application' in line and 'Host' in line and 'IP' in line:
            in_data = True
            continue
        if in_data and line and not line.startswith('Time') and not line.startswith('Constraints'):
            parts = line.split(None, 3)
            if len(parts) >= 3 and parts[0][0].isalpha() and parts[1].isdigit():
                rows.append(parts)
    
    return {'headers': ['Application', 'Host Count', 'IP Address', 'Type'], 'rows': rows} if rows else None


def extract_operating_systems(text):
    section = extract_section(text, 'Operating Systems', 'IP Traffic (SRC)')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Count' in line and 'IP Address' in line:
            in_data = True
            continue
        if in_data and line and line[0].isdigit() and '192.168' in line:
            parts = line.split(None, 4)
            if len(parts) >= 4:
                rows.append(parts)
    
    return {'headers': ['Count', 'IP Address', 'OS Vendor', 'OS Name', 'OS Version'], 'rows': rows} if rows else None


def extract_ip_traffic_src_conn(text):
    section = extract_section(text, 'IP Traffic (SRC) by Connections', 'IP Traffic (SRC) Bytes')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Initiator' in line and 'Connections' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(IP_CONN_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Initiator IP', 'Connections'], 'rows': rows} if rows else None


def extract_ip_traffic_src_bytes(text):
    section = extract_section(text, 'IP Traffic (SRC) Bytes', 'IP Traffic (SRC) Pkts')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Initiator' in line and 'Bytes' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(IP_BYTES_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Initiator IP', 'Bytes'], 'rows': rows} if rows else None


def extract_ip_traffic_src_pkts(text):
    section = extract_section(text, 'IP Traffic (SRC) Pkts', 'IP Traffic (DST)')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Initiator' in line and 'Pkts' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(IP_CONN_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Initiator IP', 'Pkts'], 'rows': rows} if rows else None


def extract_ip_traffic_dst_conn(text):
    section = extract_section(text, 'IP Traffic (DST) by Connections', 'IP Traffic (DST) Bytes')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Responder' in line and 'Connections' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(IP_CONN_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Responder IP', 'Connections'], 'rows': rows} if rows else None


def extract_ip_traffic_dst_bytes(text):
    section = extract_section(text, 'IP Traffic (DST) Bytes', 'IP Traffic (DST) Pkts')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Responder' in line and 'Bytes' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(IP_BYTES_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Responder IP', 'Bytes'], 'rows': rows} if rows else None


def extract_ip_traffic_dst_pkts(text):
    section = extract_section(text, 'IP Traffic (DST) Pkts', 'Web URL')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Responder' in line and 'Pkts' in line:
            in_data = True
            continue
        if in_data and line:
            match = re.match(IP_CONN_PATTERN, line)
            if match:
                rows.append([match.group(1), match.group(2)])
    
    return {'headers': ['Responder IP', 'Pkts'], 'rows': rows} if rows else None


def extract_web_url(text):
    section = extract_section(text, 'Web URL', 'IP Applications')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    
    for line in lines:
        if line and line[0].isdigit() and '192.168' in line:
            parts = line.split(None, 3)
            if len(parts) >= 4 and '192.168' in parts[2]:
                count, init_ip, resp_ip, rest = parts[0], parts[1], parts[2], parts[3]
                if rest[0].isdigit():
                    rest_parts = rest.split(None, 1)
                    url = rest_parts[1] if len(rest_parts) > 1 else ''
                    rows.append([count, init_ip, resp_ip, rest_parts[0], url])
                else:
                    rest_parts = rest.split()
                    if len(rest_parts) >= 2:
                        rows.append([count, init_ip, resp_ip, rest_parts[-2], rest_parts[-1]])
    
    return {'headers': ['Count', 'Initiator IP', 'Responder IP', 'Bytes', 'URL'], 'rows': rows} if rows else None


def extract_ip_applications(text):
    section = extract_section(text, 'IP Applications', 'MACs')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'Host Count' in line and 'IP Address' in line:
            in_data = True
            continue
        if in_data and line and line[0].isdigit() and '192.168' in line:
            parts = line.split(None, 3)
            if len(parts) >= 3:
                count, ip_addr, app = parts[0], parts[1], parts[2]
                rest = parts[3] if len(parts) > 3 else ''
                rest_parts = rest.split(None, 1)
                category = rest_parts[0] if rest_parts else ''
                type_field = rest_parts[1] if len(rest_parts) > 1 else ''
                rows.append([count, ip_addr, app, category, type_field])
    
    return {'headers': ['Host Count', 'IP Address', 'Application', 'Category', 'Type'], 'rows': rows} if rows else None


def extract_macs(text):
    section = extract_section(text, 'MACs', 'Intrusion Events')
    if not section:
        return None
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    in_data = False
    
    for line in lines:
        if 'MAC Address' in line and 'MAC Vendor' in line:
            in_data = True
            continue
        if in_data and line and ':' in line:
            parts = line.split(None, 1)
            if len(parts) == 2:
                rows.append(parts)
    
    return {'headers': ['MAC Address', 'MAC Vendor'], 'rows': rows} if rows else None


def parse_intrusion_event_line(line):
    parts = line.split()
    if len(parts) < 2:
        return None
    
    count = parts[0]
    snort_id = ''
    snort_idx = -1
    
    for i, part in enumerate(parts[1:], 1):
        if re.match(SNORT_ID_PATTERN, part):
            snort_id = part
            snort_idx = i
            break
    
    if not snort_id:
        return None
    
    rule_group_parts = []
    impact_idx = -1
    
    for i in range(snort_idx + 1, len(parts)):
        if parts[i] == 'Impact':
            impact_idx = i
            break
        rule_group_parts.append(parts[i])
    
    rule_group = ' '.join(rule_group_parts) if rule_group_parts else ''
    
    impact_str = ''
    if impact_idx >= 0 and impact_idx + 1 < len(parts):
        vul_parts = [parts[impact_idx + 1]]
        for j in range(impact_idx + 2, min(impact_idx + 6, len(parts))):
            vul_parts.append(parts[j])
            if ')' in parts[j]:
                break
        impact_str = ' '.join(vul_parts)
    
    ips = re.findall(IP_PATTERN, line)
    src_ip = ips[0] if ips else ''
    dst_ip = ips[1] if len(ips) > 1 else ''
    
    protocol = ''
    client = ''
    if dst_ip:
        dst_idx = line.find(dst_ip) + len(dst_ip)
        after_ips = line[dst_idx:].split()
        protocol = after_ips[0] if len(after_ips) > 0 else ''
        client = after_ips[1] if len(after_ips) > 1 else ''
    
    unique_events = ''
    trailing_nums = re.findall(TRAILING_NUMS_PATTERN, line)
    if trailing_nums:
        unique_events = trailing_nums[0].strip()
    
    return [count, snort_id, rule_group, impact_str, src_ip, dst_ip, protocol, client, unique_events]


def extract_intrusion_events(text):
    idx = text.find('Intrusion Events by Application')
    if idx == -1:
        return None
    section = text[idx:]
    
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    rows = []
    current_row_buffer = []
    in_data = False
    
    for line in lines:
        if 'Count' in line and 'Snort ID' in line:
            in_data = True
            continue
        if not in_data or not line:
            continue
        if line[0].isdigit() or (line[0] == ',' and len(line) > 1):
            if current_row_buffer:
                full_line = ' '.join(current_row_buffer)
                parsed = parse_intrusion_event_line(full_line)
                if parsed:
                    rows.append(parsed)
            current_row_buffer = [line]
        else:
            if current_row_buffer:
                current_row_buffer.append(line)
    
    if current_row_buffer:
        full_line = ' '.join(current_row_buffer)
        parsed = parse_intrusion_event_line(full_line)
        if parsed:
            rows.append(parsed)
    
    headers = [
        'Count', 'Snort ID', 'Rule Group', 'Impact',
        'Source IP', 'Destination IP', 'Application Protocol', 'Client', 'Unique Events'
    ]
    return {'headers': headers, 'rows': rows} if rows else None


def extract_all_sections(text):
    sections = {
        'Application Usage (bytes)': extract_app_usage_bytes(text),
        'Application Usage (pkts)': extract_app_usage_packets(text),
        'Web Applications': extract_web_applications(text),
        'Operating Systems': extract_operating_systems(text),
        'IP Traffic (SRC) by Connections': extract_ip_traffic_src_conn(text),
        'IP Traffic (SRC) Bytes': extract_ip_traffic_src_bytes(text),
        'IP Traffic (SRC) Pkts': extract_ip_traffic_src_pkts(text),
        'IP Traffic (DST) by Connections': extract_ip_traffic_dst_conn(text),
        'IP Traffic (DST) Bytes': extract_ip_traffic_dst_bytes(text),
        'IP Traffic (DST) Pkts': extract_ip_traffic_dst_pkts(text),
        'Web URL': extract_web_url(text),
        'IP Applications': extract_ip_applications(text),
        'MACs': extract_macs(text),
        'Intrusion Events by Application': extract_intrusion_events(text),
    }
    return {k: v for k, v in sections.items() if v and v.get('headers') and v.get('rows')}


def write_csv_output(output_file, metadata, sections_data):
    ensure_output_dir()
    base_name = os.path.basename(os.path.splitext(output_file)[0])
    output_path = os.path.join(OUTPUT_DIR, base_name)
    output_files = []
    
    csv_file = f"{output_path}_metadata.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Key', 'Value'])
        for key, value in metadata.items():
            writer.writerow([key, value])
    output_files.append(csv_file)
    
    for section_name, section_content in sections_data.items():
        if not section_content:
            continue
        safe_name = section_name.replace(' ', '_').replace('(', '').replace(')', '')
        csv_file = f"{output_path}_{safe_name}.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(section_content['headers'])
            writer.writerows(section_content['rows'])
        output_files.append(csv_file)
    
    return output_files


def print_summary(metadata, sections_data, output_files):
    print(f"\nExtracted {len(sections_data)} sections:")
    for section_name, section_content in sections_data.items():
        if section_content:
            row_count = len(section_content['rows'])
            print(f"  • {section_name}: {row_count} rows")
    
    print(f"\n{len(output_files)} CSV Files Created:")
    for output_file in output_files:
        print(f"  • {output_file}")


def process_pdf(pdf_file):
    ensure_output_dir()
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing: {pdf_file}")
    print('='*60)
    
    if not os.path.exists(pdf_file):
        print(f"Error: File not found: {pdf_file}")
        return False
    
    text = extract_text_from_pdf(pdf_file)
    if not text or len(text.strip()) < 10:
        print("Error: Could not extract meaningful text from PDF")
        return False
    
    print(f"Extracted {len(text)} characters")
    
    filename = os.path.basename(pdf_file)
    metadata = parse_metadata(text, filename)
    sections_data = extract_all_sections(text)
    
    output_csv = os.path.splitext(filename)[0] + '_parsed.csv'
    output_files = write_csv_output(output_csv, metadata, sections_data)
    
    print_summary(metadata, sections_data, output_files)
    return True


def scan_and_process_pdfs(watch_directory):
    pdf_files = glob.glob(os.path.join(watch_directory, '*.pdf'))
    
    if not pdf_files:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No PDFs found in {watch_directory}")
        return
    
    for pdf_file in pdf_files:
        if pdf_file not in PROCESSED_FILES:
            if process_pdf(pdf_file):
                PROCESSED_FILES.add(pdf_file)


def watch_directory_loop(watch_directory):
    print(f"\n{'='*60}")
    print(f"PDF Directory Watcher Started")
    print(f"{'='*60}")
    print(f"Watch Directory: {watch_directory}")
    print(f"Scan Interval: Every 24 hours")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    while True:
        try:
            scan_and_process_pdfs(watch_directory)
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Next scan in 24 hours...")
            time.sleep(86400)
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Watcher stopped by user.")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error during watch: {e}")
            time.sleep(60)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Watch directory: python3 pdf_parser.py <directory>")
        print("  Process single PDF: python3 pdf_parser.py --single <pdf_file>")
        sys.exit(1)
    
    if '--single' in sys.argv:
        single_idx = sys.argv.index('--single')
        if single_idx + 1 < len(sys.argv):
            pdf_file = sys.argv[single_idx + 1]
            process_pdf(pdf_file)
        else:
            print("Error: --single requires a file path")
            sys.exit(1)
    else:
        watch_dir = sys.argv[1]
        if not os.path.isdir(watch_dir):
            print(f"Error: {watch_dir} is not a valid directory")
            sys.exit(1)
        watch_directory_loop(watch_dir)


if __name__ == '__main__':
    main()
