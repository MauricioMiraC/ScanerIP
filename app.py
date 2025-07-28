from flask import Flask, render_template, request
import subprocess
import platform
import socket
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

app = Flask(__name__)

# Definimos las subredes disponibles
SUBNETS = [
    {"name": "Subred Principal", "base": "10.6.108"},
    {"name": "Subred Secundaria", "base": "10.6.251"},
    {"name": "Subred Secundaria", "base": "10.63.48"}
]

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def resolve_hostname(ip):
    try:
        socket.setdefaulttimeout(1)
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname.split('.')[0]
    except:
        return "No identificado"

def check_device(ip):
    ping_cmd = ['ping', '-n', '1', '-w', '200'] if platform.system().lower() == 'windows' else ['ping', '-c', '1', '-W', '1']
    try:
        subprocess.check_output(ping_cmd + [ip], stderr=subprocess.STDOUT, timeout=1)
        status = True
    except:
        status = False
    
    hostname = resolve_hostname(ip)
    return ip, status, hostname

def scan_network(base_ip):
    ips_to_scan = [f"{base_ip}.{i}" for i in range(1, 255)]
    results = []
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_device, ip): ip for ip in ips_to_scan}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                results.append(future.result(timeout=2))
            except:
                results.append((ip, False, "Error al escanear"))
    
    return sorted(results, key=lambda x: int(x[0].split('.')[-1]))

@app.route('/', methods=['GET', 'POST'])
def index():
    local_ip = get_local_ip()
    selected_subnet = request.form.get('subnet', SUBNETS[0]['base'])
    
    # Encontrar la subred seleccionada
    current_subnet = next((s for s in SUBNETS if s['base'] == selected_subnet), SUBNETS[0])
    
    start_time = time.time()
    ip_status = scan_network(current_subnet['base'])
    scan_time = round(time.time() - start_time, 2)
    
    ip_status_with_order = [(ip, status, hostname, idx) 
                          for idx, (ip, status, hostname) in enumerate(ip_status)]
    
    return render_template('index.html', 
                         local_ip=local_ip,
                         current_subnet=current_subnet,
                         ip_status=ip_status_with_order,
                         subnets=SUBNETS,
                         active_count=sum(1 for _, status, _, _ in ip_status_with_order if status),
                         inactive_count=sum(1 for _, status, _, _ in ip_status_with_order if not status),
                         scan_time=scan_time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)