import requests
import json
import datetime
import webview
import threading
import os
from time import sleep
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import sys
from tkinter import Tk, filedialog

# 禁用 urllib3 的安全警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 全局配置 ---
DEFAULT_TOKEN_DIR = os.path.join(os.path.expanduser("~"), "跑步打卡Token")
if not os.path.exists(DEFAULT_TOKEN_DIR):
    os.makedirs(DEFAULT_TOKEN_DIR)

# --- HTML 前端界面 (新增Token管理功能) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>跑步自动打卡工具</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
            padding: 20px; 
            user-select: none; 
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .container { 
            width: 100%;
            max-width: 450px; 
            background: rgba(255, 255, 255, 0.75); 
            backdrop-filter: blur(12px); 
            -webkit-backdrop-filter: blur(12px); 
            padding: 30px; 
            border-radius: 16px; 
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.4);
        }

        h2 { text-align: center; color: #333; margin-bottom: 25px; margin-top: 0; }
        
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #444; font-weight: 600; font-size: 0.9em;}
        
        input, select { 
            width: 100%; 
            padding: 12px; 
            border: 1px solid rgba(0,0,0,0.1); 
            border-radius: 8px; 
            box-sizing: border-box; 
            transition: 0.3s; 
            background: rgba(255, 255, 255, 0.9);
            font-size: 14px;
        }
        
        input:focus, select:focus { 
            border-color: #764ba2; 
            outline: none; 
            box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.2); 
        }
        
        button { 
            width: 100%; 
            padding: 14px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 8px; 
            font-size: 16px; 
            cursor: pointer; 
            transition: 0.3s; 
            font-weight: bold; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            margin-bottom: 10px;
        }
        
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        }
        
        button:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
            transform: none;
            box-shadow: none;
        }
        
        #log-area { 
            margin-top: 25px; 
            height: 180px; 
            overflow-y: auto; 
            background: rgba(45, 45, 45, 0.9); 
            color: #00ff00; 
            padding: 15px; 
            border-radius: 8px; 
            font-family: 'Consolas', monospace; 
            font-size: 12px; 
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        }
        
        #log-area::-webkit-scrollbar { width: 8px; }
        #log-area::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
        #log-area::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }

        .log-entry { margin-bottom: 4px; border-bottom: 1px solid #444; padding-bottom: 2px; word-break: break-all;}
        .error { color: #ff6b6b; }
        .success { color: #51cf66; font-weight: bold; }
        
        .token-group {
            background: rgba(240, 240, 255, 0.8);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid rgba(118, 75, 162, 0.2);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #88a0e8 0%, #9874c2 100%);
            padding: 8px 12px;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .small-btn {
            width: auto;
            padding: 8px 12px;
            font-size: 14px;
            margin-left: 5px;
        }
        
        .flex-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .flex-row > * {
            flex: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>🏃一师跑步打卡助手</h2>
        
        <!-- Token管理区域 -->
        <div class="token-group">
            <h3 style="margin-top:0; color: #555; font-size: 16px;">🔑 Token管理</h3>
            <div class="form-group">
                <label>Token保存目录</label>
                <div style="display: flex; gap: 8px;">
                    <input type="text" id="tokenDir" placeholder="选择Token保存文件夹" readonly>
                    <button class="small-btn" onclick="selectTokenDir()">选择</button>
                </div>
            </div>
            <div class="form-group">
                <label>已保存的Token (选择后可直接使用)</label>
                <select id="savedTokens">
                    <option value="">-- 暂无保存的Token --</option>
                </select>
                <button class="btn-secondary" onclick="loadSelectedToken()">使用选中的Token</button>
                <button class="btn-secondary" onclick="refreshTokenList()">刷新Token列表</button>
            </div>
        </div>

        <div class="form-group">
            <label>学号/账号</label>
            <input type="text" id="username" placeholder="请输入学号">
        </div>
        <div class="form-group">
            <label>密码</label>
            <input type="password" id="password" placeholder="请输入密码">
        </div>
        <div class="flex-row">
            <div class="form-group" style="margin-bottom:0;">
                <label>平均速度 (m/s)</label>
                <input type="number" id="speed" step="0.01" value="2.5">
            </div>
            <div class="form-group" style="margin-bottom:0;">
                <label>跑步里程 (km)</label>
                <input type="number" id="mileage" step="0.1" value="4.0">
            </div>
        </div>
        
        <button id="runBtn" onclick="startRun()">开始跑步</button>
        <button class="btn-secondary" onclick="clearTokenDir()">清空Token目录</button>
        
        <div id="log-area"></div>
    </div>

    <script>
        // 初始化Token目录
        window.onload = function() {
            pywebview.api.get_default_token_dir().then(dir => {
                document.getElementById('tokenDir').value = dir;
                refreshTokenList();
            });
        }

        function log(msg, type='') {
            const logArea = document.getElementById('log-area');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
            logArea.appendChild(entry);
            logArea.scrollTop = logArea.scrollHeight;
        }

        function startRun() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const speed = document.getElementById('speed').value;
            const mileage = document.getElementById('mileage').value;
            const tokenDir = document.getElementById('tokenDir').value;

            if(!username || !password) {
                log('错误：请填写账号和密码', 'error');
                return;
            }
            
            if(!tokenDir) {
                log('错误：请选择Token保存目录', 'error');
                return;
            }

            document.getElementById('runBtn').disabled = true;
            document.getElementById('runBtn').innerText = "正在运行...";
            log('正在启动任务...', 'info');

            // 调用 Python 后端
            pywebview.api.start_process(username, password, speed, mileage, tokenDir)
                .catch(err => {
                    log('系统错误: ' + err, 'error');
                    resetBtn();
                });
        }

        function resetBtn() {
            document.getElementById('runBtn').disabled = false;
            document.getElementById('runBtn').innerText = "开始跑步";
        }
        
        // Token管理相关函数
        function selectTokenDir() {
            pywebview.api.select_token_directory().then(dir => {
                if(dir) {
                    document.getElementById('tokenDir').value = dir;
                    refreshTokenList();
                    log(`Token目录已设置为: ${dir}`, 'success');
                }
            });
        }
        
        function refreshTokenList() {
            const tokenDir = document.getElementById('tokenDir').value;
            pywebview.api.get_saved_tokens(tokenDir).then(tokens => {
                const select = document.getElementById('savedTokens');
                select.innerHTML = '';
                
                if(tokens.length === 0) {
                    select.innerHTML = '<option value="">-- 暂无保存的Token --</option>';
                    return;
                }
                
                tokens.forEach(tokenFile => {
                    const option = document.createElement('option');
                    option.value = tokenFile;
                    option.textContent = tokenFile.replace('.json', ''); // 显示学号
                    select.appendChild(option);
                });
            });
        }
        
        function loadSelectedToken() {
            const tokenDir = document.getElementById('tokenDir').value;
            const selectedFile = document.getElementById('savedTokens').value;
            
            if(!selectedFile) {
                log('请先选择一个已保存的Token', 'error');
                return;
            }
            
            pywebview.api.load_token_from_file(tokenDir, selectedFile).then(result => {
                if(result.success) {
                    // 提取学号并填充到用户名输入框
                    const username = selectedFile.replace('.json', '');
                    document.getElementById('username').value = username;
                    log(`成功加载 ${username} 的Token，可直接点击开始跑步（无需输入密码）`, 'success');
                } else {
                    log(`加载Token失败: ${result.error}`, 'error');
                }
            });
        }
        
        function clearTokenDir() {
            if(confirm('确定要清空Token目录吗？此操作不可恢复！')) {
                const tokenDir = document.getElementById('tokenDir').value;
                pywebview.api.clear_token_directory(tokenDir).then(success => {
                    if(success) {
                        log('Token目录已清空', 'success');
                        refreshTokenList();
                    } else {
                        log('清空Token目录失败', 'error');
                    }
                });
            }
        }
    </script>
</body>
</html>
"""

# --- 核心逻辑类 ---
class CoreLogic:
    def __init__(self, logger_callback):
        self.log = logger_callback
        self.current_token_dir = DEFAULT_TOKEN_DIR
        self.loaded_token = None

    def set_token_dir(self, token_dir):
        """设置Token保存目录"""
        if token_dir and os.path.isdir(token_dir):
            self.current_token_dir = token_dir
            self.log(f"Token保存目录已设置为: {self.current_token_dir}")
        else:
            self.log(f"无效的目录: {token_dir}，使用默认目录", 'error')

    def get_token_file_path(self, username):
        """获取指定学号的Token文件路径"""
        return os.path.join(self.current_token_dir, f"{username}.json")

    def save_token(self, username, token):
        """保存Token，文件名为 学号.json"""
        try:
            token_file = self.get_token_file_path(username)
            with open(token_file, 'w', encoding='utf-8') as f:
                json.dump({'token': token, 'save_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
            self.log(f"Token已保存至: {token_file}", 'success')
            self.loaded_token = token
        except Exception as e:
            self.log(f"保存token失败: {e}", 'error')

    def load_token(self, username=None):
        """
        加载Token
        - 如果指定username，加载对应学号的Token
        - 如果未指定，使用已加载的Token
        """
        if username:
            token_file = self.get_token_file_path(username)
            if os.path.exists(token_file):
                try:
                    with open(token_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.loaded_token = data.get('token')
                        self.log(f"成功加载 {username} 的Token")
                        return self.loaded_token
                except Exception as e:
                    self.log(f"加载 {username} 的Token失败: {e}", 'error')
                    self.loaded_token = None
                    return None
            else:
                self.log(f"未找到 {username} 的Token文件", 'error')
                return None
        return self.loaded_token

    def load_token_from_file(self, token_dir, filename):
        """从指定文件加载Token"""
        try:
            file_path = os.path.join(token_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.loaded_token = data.get('token')
                    username = filename.replace('.json', '')
                    self.log(f"成功加载 {username} 的Token")
                    return {'success': True, 'token': self.loaded_token}
            else:
                return {'success': False, 'error': '文件不存在'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_saved_tokens(self, token_dir):
        """获取指定目录下所有的Token文件"""
        try:
            if not os.path.exists(token_dir):
                return []
            # 筛选出 .json 结尾的文件，且文件名符合学号格式（纯数字）
            token_files = [f for f in os.listdir(token_dir) 
                          if f.endswith('.json') and f.replace('.json', '').isdigit()]
            return sorted(token_files)
        except Exception as e:
            self.log(f"获取Token列表失败: {e}", 'error')
            return []

    def clear_token_directory(self, token_dir):
        """清空指定目录下的所有Token文件"""
        try:
            token_files = self.get_saved_tokens(token_dir)
            for file in token_files:
                file_path = os.path.join(token_dir, file)
                os.remove(file_path)
            self.log(f"已清空 {token_dir} 目录下的 {len(token_files)} 个Token文件", 'success')
            self.loaded_token = None
            return True
        except Exception as e:
            self.log(f"清空Token目录失败: {e}", 'error')
            return False

    def is_token_valid(self, session, bearer_token):
        if not bearer_token:
            return False
        try:
            headers = {
                'Authorization': bearer_token,
                'user-agent': 'Mozilla/5.0 (Linux; Android 12; V2344A Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/95.0.4638.74 Safari/537.36 uni-app Html5Plus/1.0 (Immersed/0.5714286)',
                'Host': 'lb.hnfnu.edu.cn',
            }
            response = session.get(
                'https://lb.hnfnu.edu.cn/system/user/profile',
                headers=headers,
                verify=False,
                timeout=10
            )
            response_data = response.json()
            return response_data.get('code') == 200
        except Exception as e:
            self.log(f"Token验证异常: {e}", 'error')
            return False

    def login(self, session, username, password):
        # 先尝试加载该学号的Token
        saved_token = self.load_token(username)
        if saved_token:
            self.log(f"检测到 {username} 的本地Token，正在验证有效性...")
            if self.is_token_valid(session, saved_token):
                self.log(f"{username} 本地Token有效，免密登录成功", 'success')
                return saved_token
            else:
                self.log(f"{username} 本地Token已失效", 'error')

        self.log(f"正在尝试使用账号 {username} 登录...")
        headers = {
            'user-agent': 'Mozilla/5.0 (Linux; Android 12; V2344A Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/95.0.4638.74 Safari/537.36 uni-app Html5Plus/1.0 (Immersed/0.5714286)',
            'Content-Type': 'application/json',
            'Host': 'lb.hnfnu.edu.cn',
        }
        json_data = {
            'username': username,
            'password': password,
            'code': '',
            'uuid': '',
        }
        try:
            response = session.post('https://lb.hnfnu.edu.cn/login', headers=headers, json=json_data, verify=False)
            response_data = response.json()
            
            if response_data.get('code') == 500:
                self.log('登录失败：账号或密码错误', 'error')
                return None
            else:
                token = response_data.get('token')
                if token:
                    bearer_token = f"Bearer {token}"
                    self.save_token(username, bearer_token)  # 保存为 学号.json
                    self.log("登录成功，Token已更新", 'success')
                    return bearer_token
                return None
        except Exception as e:
            self.log(f"网络请求失败: {e}", 'error')
            return None

    def encrypt_timestamp(self, custom_date=None):
        key = "lanbu123456hndys".encode('utf-8')
        try:
            if custom_date:
                if isinstance(custom_date, datetime.datetime):
                    custom_date = custom_date.strftime("%Y-%m-%d %H:%M:%S")
                date = datetime.datetime.strptime(custom_date, "%Y-%m-%d %H:%M:%S")
            else:
                date = datetime.datetime.now()
            timestamp = str(int(date.timestamp() * 1000))
            
            cipher = AES.new(key, AES.MODE_ECB)
            encrypted_bytes = cipher.encrypt(pad(timestamp.encode('utf-8'), AES.block_size))
            encrypted = base64.b64encode(encrypted_bytes).decode('utf-8')
            split_index = (len(encrypted) + 1) // 2
            header_part = encrypted[:split_index]
            body_part = encrypted[split_index:]
            return {
                'headerPart': header_part,
                'bodyPart': body_part
            }
        except ValueError:
            self.log("日期加密错误", 'error')
            return None

    def start_page(self, session, bearer_token, now):
        headers = {
            'Authorization': bearer_token,
            'user-agent': 'Mozilla/5.0 (Linux; Android 12; V2344A Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/95.0.4638.74 Safari/537.36 uni-app Html5Plus/1.0 (Immersed/0.5714286)',
            'Content-Type': 'application/json',
            'Host': 'lb.hnfnu.edu.cn',
        }
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        json_data = {
            'dlatitude': '29.193135',
            'dlongitude': '115.865848',
            'startTime': formatted_time,
        }
        try:
            self.log("正在获取打卡位置ID...")
            response = session.post('https://lb.hnfnu.edu.cn/school/student/addLMRanking', headers=headers, json=json_data, verify=False)
            return response.json().get('data')
        except Exception as e:
            self.log(f"获取位置ID失败: {e}", 'error')
            return None

    def submit_info(self, session, bearer_token, id, speed, mileage, now):
        # 强制格式化小数位
        speed = round(float(speed), 2) if speed else 2.5
        mileage = round(float(mileage), 1) if mileage else 2.0

        self.log(f"开始模拟跑步: 里程 {mileage}km, 速度 {speed}m/s")
        
        # 计算需要的时间
        duration_seconds = (mileage * 1000) / speed
        new_time = now + datetime.timedelta(seconds=duration_seconds)
        formatted_time = new_time.strftime("%Y-%m-%d %H:%M:%S")

        total_seconds = round(duration_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.log(f"模拟耗时: {time_str} (将在 {formatted_time} 结束)")
        self.log("等待服务器同步 (5秒)...")
        sleep(5) 

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = self.encrypt_timestamp(now_str)

        headers = {
            'custom-header': result['headerPart'],
            'Authorization': bearer_token,
            'user-agent': 'Mozilla/5.0 (Linux; Android 12; V2344A Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/95.0.4638.74 Safari/537.36 uni-app Html5Plus/1.0 (Immersed/0.5714286)',
            'Content-Type': 'application/json',
            'Host': 'lb.hnfnu.edu.cn',
        }
        json_data = {
            'id': id,
            'state': '等待',
            'mileage': mileage,
            'mileageSum': mileage,
            'formattedTime': time_str,
            'overTime': formatted_time,
            'speed': speed,
            'bodyPart': result['bodyPart']
        }
        
        try:
            self.log("正在提交跑步数据...")
            response = session.post('https://lb.hnfnu.edu.cn/school/student/longMarchSpeed', headers=headers, json=json_data, verify=False)
            data_dict = response.json()
            
            if 'data' in data_dict and 'Grade' in data_dict['data']:
                grade = data_dict['data']['Grade']
                self.log(f"✅ 跑步成功！获得分数: {grade}", 'success')
            else:
                msg = data_dict.get('msg', '未知错误')
                self.log(f"❌ 跑步失败: {msg}", 'error')
        except Exception as e:
            self.log(f"提交数据异常: {e}", 'error')

# --- API 桥接类 ---
class Api:
    def __init__(self):
        self.window = None
        self.logic = None

    def set_window(self, window):
        self.window = window
        # 初始化核心逻辑，传入日志回调
        self.logic = CoreLogic(self.log)

    def log(self, message, type=''):
        print(f"LOG: {message}")
        if self.window:
            # 转义单引号避免JS语法错误
            safe_message = message.replace("'", "\\'").replace('"', '\\"')
            self.window.evaluate_js(f"log('{safe_message}', '{type}')")

    def reset_ui_button(self):
        if self.window:
            self.window.evaluate_js("resetBtn()")

    # --- Token管理相关API ---
    def get_default_token_dir(self):
        """获取默认Token目录"""
        return DEFAULT_TOKEN_DIR

    def select_token_directory(self):
        """打开文件夹选择对话框"""
        root = Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes('-topmost', True)  # 置顶
        folder_path = filedialog.askdirectory(title="选择Token保存目录")
        root.destroy()
        return folder_path

    def get_saved_tokens(self, token_dir):
        """获取指定目录下的Token文件列表"""
        return self.logic.get_saved_tokens(token_dir)

    def load_token_from_file(self, token_dir, filename):
        """从指定文件加载Token"""
        return self.logic.load_token_from_file(token_dir, filename)

    def clear_token_directory(self, token_dir):
        """清空Token目录"""
        return self.logic.clear_token_directory(token_dir)

    # --- 主流程 ---
    def start_process(self, username, password, speed, mileage, token_dir):
        """启动打卡流程"""
        # 在新线程中运行
        t = threading.Thread(target=self._run_background, args=(username, password, speed, mileage, token_dir))
        t.start()

    def _run_background(self, username, password, speed, mileage, token_dir):
        # 设置Token保存目录
        self.logic.set_token_dir(token_dir)
        
        session = requests.Session()

        try:
            bearer_token = self.logic.login(session, username, password)
            
            if bearer_token:
                sleep(1)
                self.log("获取用户信息...")
                now = datetime.datetime.now()
                run_id = self.logic.start_page(session, bearer_token, now)
                
                if run_id:
                    self.log(f"获取到 Run ID: {run_id}")
                    self.logic.submit_info(session, bearer_token, run_id, speed, mileage, now)
                else:
                    self.log("无法初始化跑步任务", 'error')
            else:
                self.log("登录流程未完成，停止运行", 'error')

        except Exception as e:
            self.log(f"发生未捕获异常: {e}", 'error')
        finally:
            self.reset_ui_button()

# --- 主入口 ---
if __name__ == '__main__':
    api = Api()
    window = webview.create_window(
        '跑步自动打卡', 
        html=HTML_CONTENT, 
        width=550, 
        height=850, 
        resizable=True, 
        js_api=api 
    )
    api.set_window(window)
    webview.start()