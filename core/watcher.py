import os
import sys
import time
import subprocess
import signal
import threading
import json
import socket
import http.server
import socketserver
import webbrowser
import hashlib
from generator import generate, load_config

global_mtime = time.time()

class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()

    def do_GET(self):
        global global_mtime
        if self.path == '/livereload_status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            # We don't call super().end_headers() here because we already sent our own and don't want the default ones
            http.server.SimpleHTTPRequestHandler.end_headers(self)
            self.wfile.write(json.dumps({'mtime': global_mtime}).encode())
        elif self.path == '/force_refresh':
            # This endpoint allows the user to manually force a rebuild
            project_dir = getattr(self.server, 'project_dir', '.')
            print("\nManual refresh requested! Rebuilding...")
            generate(project_dir, is_watch=True)
            global_mtime = time.time()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            http.server.SimpleHTTPRequestHandler.end_headers(self)
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        elif self.path == '/livereload.js':
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript')
            self.send_header('Cache-Control', 'no-store')
            http.server.SimpleHTTPRequestHandler.end_headers(self)
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'livereload.js')
            if os.path.exists(script_path):
                with open(script_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"console.error('livereload.js not found');")
        else:
            # If the user hits Ctrl+R on the main page, force a rebuild as well
            if self.path.endswith('.html'):
                project_dir = getattr(self.server, 'project_dir', '.')
                generate(project_dir, is_watch=True)
                global_mtime = time.time()
                
            super().do_GET()
            
    def log_message(self, format, *args):
        pass # Suppress logging

def get_pid_file(project_dir):
    config_dir = os.path.expanduser("~/.config/ok")
    os.makedirs(config_dir, exist_ok=True)
    project_hash = hashlib.md5(os.path.abspath(project_dir).encode('utf-8')).hexdigest()
    return os.path.join(config_dir, f"watch_{project_hash}.pid")

def get_watch_targets(project_dir):
    config = load_config(project_dir)
    targets = config.get('watch_targets', 'data,templates,styles,config.cfg')
    return [t.strip() for t in targets.split(',')]

def get_export_targets(project_dir):
    config = load_config(project_dir)
    return config.get('export_target', 'both').lower()

def scan_files(project_dir, targets):
    latest_mtime = 0
    file_count = 0
    for target in targets:
        target_path = os.path.join(project_dir, target)
        if not os.path.exists(target_path):
            continue
            
        if os.path.isfile(target_path):
            file_count += 1
            mtime = os.path.getmtime(target_path)
            if mtime > latest_mtime:
                latest_mtime = mtime
        else:
            for root, _, files in os.walk(target_path):
                # Also include directory mtimes so deleted folders are detected
                dir_mtime = os.path.getmtime(root)
                if dir_mtime > latest_mtime:
                    latest_mtime = dir_mtime
                    
                for file in files:
                    file_count += 1
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_mtime:
                        latest_mtime = mtime
    return latest_mtime, file_count

def watch_loop(project_dir):
    global global_mtime
    pid_file = get_pid_file(project_dir)
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
        
    print(f"Started watching {project_dir} (PID: {os.getpid()})")
    
    export_dir = os.path.join(project_dir, 'export')
    os.makedirs(export_dir, exist_ok=True)
    
    # Run initial build
    generate(project_dir, is_watch=True)
    global_mtime = time.time()
    
    # Start web server for live preview
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
        
    class Handler(LiveReloadHandler):
        def __init__(self, *args, **kwargs):
            try:
                super().__init__(*args, directory=export_dir, **kwargs)
            except TypeError:
                os.chdir(export_dir)
                super().__init__(*args, **kwargs)
                
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), Handler)
    httpd.project_dir = project_dir # pass project_dir to the server for force rebuilds
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    
    project_name = os.path.basename(os.path.normpath(os.path.abspath(project_dir)))
    url = f"http://localhost:{port}/{project_name}.html"
    print(f"\nLive Preview running at: {url}\n")
    webbrowser.open(url)
    
    try:
        targets = get_watch_targets(project_dir)
        last_mtime, last_count = scan_files(project_dir, targets)
        
        while True:
            time.sleep(0.5) # Poll every 0.5s for snappy response
            
            targets = get_watch_targets(project_dir)
            current_mtime, current_count = scan_files(project_dir, targets)
            
            if current_mtime > last_mtime or current_count != last_count:
                print("Changes detected! Rebuilding...")
                generate(project_dir, is_watch=True)
                global_mtime = time.time()
                last_mtime = current_mtime
                last_count = current_count
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)
        print("\nStopped watching.")

def start_watch(project_dir):
    pid_file = get_pid_file(project_dir)
    if os.path.exists(pid_file):
        print("Watch process is already running for this project.")
        return
        
    # Spawn background process
    script_path = os.path.abspath(__file__)
    subprocess.Popen([sys.executable, script_path, "run", project_dir],
                     stdout=sys.stdout, stderr=sys.stderr)

def stop_watch(project_dir):
    pid_file = get_pid_file(project_dir)
    if not os.path.exists(pid_file):
        print("No active watch process found for this project.")
        return
        
    with open(pid_file, 'r') as f:
        pid_str = f.read().strip()
        
    if pid_str.isdigit():
        pid = int(pid_str)
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped watch process (PID: {pid}).")
        except ProcessLookupError:
            print("Process not found. It might have already exited.")
    os.remove(pid_file)

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "run":
        watch_loop(sys.argv[2])
