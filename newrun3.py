import requests
import json
import time
import random
import sys
from datetime import datetime, timedelta

# ================= 配置区 =================
USERNAME = "你的学号"
PASSWORD = "你的密码"  # 请确保密码正确
TARGET_KM = 2.90        # 目标里程 (km)
TARGET_SPEED = 2.5     # 目标速度 (m/s)，建议 1.5 - 5.5
# 请务必保留或更新你抓包到的完整 deviceid
DEVICE_ID = '{"deviceBrand":"microsoft","deviceId":"17743449642521685505","deviceType":"phone","system":"Windows 11 x64"}'
# =========================================

BASE_URL = "https://ledong.hnfnu.edu.cn/backend"
HEADERS = {
    "Host": "ledong.hnfnu.edu.cn",
    "xweb_xhr": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781",
    "Content-Type": "application/json",
    "Referer": "https://servicewechat.com/wx7caac81721cd7ef6/33/page-frame.html"
}

def format_duration(seconds):
    """将秒数格式化为 HH:mm:ss"""
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def countdown_timer(seconds):
    """在控制台显示动态倒计时"""
    print(f"\n[!] 服务器校验严格物理时间，脚本将挂机等待 {format_duration(seconds)}")
    print("[*] 请不要关闭此窗口，保持网络畅通...")
    try:
        for remaining in range(int(seconds), 0, -1):
            sys.stdout.write(f"\r🏃 模拟跑步中... 剩余时间: {format_duration(remaining)} ")
            sys.stdout.flush()
            time.sleep(1)
        print("\n\n✅ 模拟运动时长达成！正在准备提交...")
    except KeyboardInterrupt:
        print("\n\n🛑 用户中止了运行。成绩未提交。")
        sys.exit()

def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    print(f"[*] 正在登录用户: {USERNAME}...")
    login_data = {"username": USERNAME, "password": PASSWORD, "deviceid": DEVICE_ID}
    try:
        res = s.post(f"{BASE_URL}/login", json=login_data).json()
        if res.get("code") == 200:
            s.headers.update({"Authorization": f"Bearer {res.get('token')}"})
            print("✅ 登录成功")
            return s
        else:
            print(f"❌ 登录失败: {res.get('msg')}")
            return None
    except Exception as e:
        print(f"❌ 网络请求异常: {e}")
        return None

def start_run_sign(session):
    """第一步：向服务器申请跑步 ID (addLMRanking)"""
    print("[*] 正在同步打卡点位并向服务器申请跑步 ID...")
    # 模拟真实点击地图行为
    session.get(f"{BASE_URL}/getInfo")
    points_data = session.get(f"{BASE_URL}/school/student/LongMarchList").json()
    
    if points_data.get("code") != 200:
        print("❌ 获取点位失败，请检查网络或 Token")
        return None
    
    # 选第一个点作为起点
    first_pt = points_data['rows'][0]
    lat, lng = first_pt['latitude'], first_pt['longitude']
    
    sign_payload = {
        "dlatitude": str(lat),
        "dlongitude": str(lng),
        "location": json.dumps({
            "latitude": float(lat),
            "longitude": float(lng),
            "speed": 0, "accuracy": 30, "altitude": 35.5
        }),
        "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    res = session.post(f"{BASE_URL}/school/student/addLMRanking", json=sign_payload).json()
    run_id = res.get("data")
    
    if run_id == -1:
        print("⚠️ 提示：今日跑步公里数已达上限，无需再跑。")
        return None
    elif res.get("code") == 200:
        print(f"✅ 签到成功！本次跑步 ID 为: {run_id}")
        return run_id, first_pt
    else:
        print(f"❌ 开启跑步记录失败: {res.get('msg')}")
        return None

def submit_result(session, run_id, start_pt, total_seconds):
    """第二步：构造轨迹并最终提交 (longMarchSpeed)"""
    time_str = format_duration(total_seconds)
    history = []
    # 轨迹点时间戳从“现在”往前推，模拟 10 个附近的点
    start_ts = int(time.time() * 1000) - int(total_seconds * 1000)
    
    for i in range(10):
        history.append({
            "latitude": round(float(start_pt['latitude']) + random.uniform(-0.0001, 0.0001), 6),
            "longitude": round(float(start_pt['longitude']) + random.uniform(-0.0001, 0.0001), 6),
            "timestamp": start_ts + (i * 5000),
            "altitude": 35.0
        })

    submit_payload = {
        "id": int(run_id),
        "mileageInt": TARGET_KM,
        "mileage": TARGET_KM,
        "speed": str(TARGET_SPEED),
        "formattedTime": time_str,
        "overTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history": json.dumps(history),
        "state": "成功"
    }
    
    res = session.post(f"{BASE_URL}/school/student/longMarchSpeed", json=submit_payload).json()
    if res.get("code") == 200:
        print(f"🎉 提交成功！服务器消息: {res.get('msg')}")
    else:
        print(f"❌ 提交失败: {res.get('msg')}")

def main():
    # 计算理论耗时
    total_seconds = int((TARGET_KM * 1000) / TARGET_SPEED)
    
    session = get_session()
    if session:
        # 1. 签到 (获取服务器 ID 并留下开始时间戳)
        sign_info = start_run_sign(session)
        if sign_info:
            run_id, start_pt = sign_info
            
            # 2. 硬核等待 (关键环节：避开“人类极限速度”校验)
            countdown_timer(total_seconds)
            
            # 3. 提交结果
            submit_result(session, run_id, start_pt, total_seconds)

if __name__ == "__main__":
    main()
