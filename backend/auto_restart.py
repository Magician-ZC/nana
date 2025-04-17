import os
import subprocess
import time
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RestartHandler(FileSystemEventHandler):
    def __init__(self, server_process):
        self.server_process = server_process
        self.last_restart = time.time()
        self.cooldown = 5  # 冷却时间（秒）
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if time.time() - self.last_restart < self.cooldown:
            return
            
        filename = os.path.basename(event.src_path)
        if filename in ['main.py', 'qiniu_uploader.py']:
            print(f"检测到文件变化: {filename}，重启服务器...")
            
            # 终止当前进程
            if self.server_process:
                try:
                    self.server_process.terminate()
                    self.server_process.wait(5)
                except:
                    print("强制终止进程...")
                    try:
                        self.server_process.kill()
                    except:
                        pass
            
            # 启动新的服务器进程
            self.server_process = start_server()
            self.last_restart = time.time()

def start_server():
    """启动uvicorn服务器"""
    # 使用相对路径启动服务器
    print("启动服务器...")
    process = subprocess.Popen(
        ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # 等待服务器启动
    time.sleep(2)
    return process

if __name__ == "__main__":
    # 启动初始服务器
    server_process = start_server()
    
    # 设置文件监听
    event_handler = RestartHandler(server_process)
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=False)
    observer.start()
    
    try:
        print("文件监视器已启动. 按Ctrl+C停止.")
        
        # 持续输出服务器日志
        while True:
            if server_process:
                # 输出标准输出
                for line in iter(server_process.stdout.readline, ""):
                    if not line:
                        break
                    print(f"[SERVER]: {line.strip()}")
                
                # 输出标准错误
                for line in iter(server_process.stderr.readline, ""):
                    if not line:
                        break
                    print(f"[SERVER ERROR]: {line.strip()}")
                    
            time.sleep(0.1)
        
    except KeyboardInterrupt:
        print("停止服务...")
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(5)
            except:
                server_process.kill()
        observer.stop()
    
    observer.join() 