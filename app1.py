from flask import Flask, render_template
import subprocess
import platform
import socket
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

app = Flask(__name__)

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
    """Versión simplificada y robusta para resolver nombres"""
    try:
        # Timeout para la resolución DNS
        socket.setdefaulttimeout(1)
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname.split('.')[0]
    except (socket.herror, socket.gaierror, socket.timeout):
        return "No identificado"
    except:
        return "Error al resolver"

def check_device(ip):
    """Verifica el estado de un dispositivo y obtiene su nombre"""
    ping_cmd = ['ping', '-n', '1', '-w', '300'] if platform.system().lower() == 'windows' else ['ping', '-c', '1', '-W', '1']
    
    try:
        # Verificar si está activo
        subprocess.check_output(ping_cmd + [ip], 
                             stderr=subprocess.STDOUT,
                             timeout=1)
        status = True
    except:
        status = False
    
    # Obtener nombre del dispositivo (sin bloquear)
    hostname = resolve_hostname(ip)
    
    return ip, status, hostname

def scan_network(base_ip):
    """Escanea la red de manera robusta"""
    ips_to_scan = [f"{base_ip}.{i}" for i in range(1, 255)]
    results = []
    
    # Usamos ThreadPoolExecutor con manejo de errores
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_device, ip): ip for ip in ips_to_scan}
        
        for future in as_completed(futures):
            ip = futures[future]
            try:
                results.append(future.result(timeout=2))
            except Exception as e:
                results.append((ip, False, f"Error: {str(e)}"))
    
    # Ordenar por último octeto
    return sorted(results, key=lambda x: int(x[0].split('.')[-1]))

@app.route('/')
def index():
    local_ip = get_local_ip()
    base_ip = re.sub(r'\.\d+$', '', local_ip)
    
    start_time = time.time()
    ip_status = scan_network(base_ip)
    scan_time = round(time.time() - start_time, 2)
    
    # Añadir índice para animaciones
    ip_status_with_order = [(ip, status, hostname, idx) 
                           for idx, (ip, status, hostname) in enumerate(ip_status)]
    
    return render_template('index.html', 
                         local_ip=local_ip,
                         base_ip=base_ip,
                         ip_status=ip_status_with_order,
                         active_count=sum(1 for _, status, _, _ in ip_status_with_order if status),
                         inactive_count=sum(1 for _, status, _, _ in ip_status_with_order if not status),
                         scan_time=scan_time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)