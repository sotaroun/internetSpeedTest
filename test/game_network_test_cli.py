import subprocess
import platform
import re
import time
import statistics

# 測定するゲームサーバー
GAME_SERVERS = {
    "AWS Tokyo": "ec2.ap-northeast-1.amazonaws.com",
    "AWS Singapore": "ec2.ap-southeast-1.amazonaws.com"
}

def ping_host(host, count=10):
    """指定サーバーにPingを送り、平均・ジッター・標準偏差・パケロスを取得"""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = subprocess.run(["ping", param, str(count), host],
                            capture_output=True, text=True)
    output = result.stdout
    times = [float(t) for t in re.findall(r'time[=<]([0-9.]+) ms', output)]
    packet_loss = int(re.search(r'(\d+)% packet loss', output).group(1)) if re.search(r'(\d+)% packet loss', output) else 0
    avg = sum(times)/len(times) if times else 0
    jitter = max(times)-min(times) if times else 0
    stddev = statistics.stdev(times) if len(times) > 1 else 0
    return {"avg_ping": avg, "jitter": jitter, "stddev": stddev, "packet_loss": packet_loss}

def test_speed():
    """speedtest CLIを実行し、ダウンロード・アップロード・Pingを取得"""
    try:
        result = subprocess.run(["speedtest", "--simple"], capture_output=True, text=True)
        output = result.stdout
        # 出力から数値を抽出
        download = float(re.search(r"Download: ([0-9.]+) Mbit/s", output).group(1))
        upload = float(re.search(r"Upload: ([0-9.]+) Mbit/s", output).group(1))
        ping = float(re.search(r"Ping: ([0-9.]+) ms", output).group(1))
        return {"download": download, "upload": upload, "ping": ping}
    except Exception as e:
        print("Speedtest測定に失敗:", e)
        return {"download": 0, "upload": 0, "ping": 0}

def evaluate_stability(ping_std, jitter, packet_loss):
    """安定性判定"""
    if ping_std < 5 and jitter < 10 and packet_loss == 0:
        return "安定"
    elif ping_std < 10 and jitter < 20 and packet_loss < 1:
        return "普通"
    else:
        return "注意"

def main():
    print("=== ゲーム向け通信品質測定（CLI版） ===\n")
    
    # インターネット速度測定
    speed = test_speed()
    print(f"ダウンロード: {speed['download']:.2f} Mbps")
    print(f"アップロード: {speed['upload']:.2f} Mbps")
    print(f"Ping（ISP経路）: {speed['ping']:.2f} ms\n")

    # ゲームサーバーPing測定
    print("ゲームサーバーPing測定（安定性含む）:")
    for name, host in GAME_SERVERS.items():
        result = ping_host(host)
        stability = evaluate_stability(result['stddev'], result['jitter'], result['packet_loss'])
        print(f"{name} - 平均Ping: {result['avg_ping']:.2f} ms, "
              f"ジッター: {result['jitter']:.2f} ms, "
              f"標準偏差: {result['stddev']:.2f}, "
              f"パケロス: {result['packet_loss']}%, "
              f"安定性: {stability}")

if __name__ == "__main__":
    main()
