#  安定性測定用にジッターと標準偏差を追加

import subprocess
import platform
import re
import time
import statistics
import speedtest

GAME_SERVERS = {
    "AWS Tokyo": "ec2.ap-northeast-1.amazonaws.com",
    "AWS Singapore": "ec2.ap-southeast-1.amazonaws.com"
}

def ping_host(host, count=10):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = subprocess.run(["ping", param, str(count), host],
                            capture_output=True, text=True)
    output = result.stdout
    # Ping値抽出
    times = [float(t) for t in re.findall(r'time[=<]([0-9.]+) ms', output)]
    packet_loss = int(re.search(r'(\d+)% packet loss', output).group(1)) if re.search(r'(\d+)% packet loss', output) else 0
    avg = sum(times)/len(times) if times else 0
    jitter = max(times)-min(times) if times else 0
    stddev = statistics.stdev(times) if len(times) > 1 else 0
    return {"avg_ping": avg, "jitter": jitter, "stddev": stddev, "packet_loss": packet_loss}

def test_speed(repeats=3):
    st = speedtest.Speedtest()
    st.get_best_server()
    downloads, uploads = [], []
    for _ in range(repeats):
        downloads.append(st.download()/1_000_000)
        uploads.append(st.upload()/1_000_000)
        time.sleep(1)
    return {
        "download_avg": sum(downloads)/repeats,
        "download_std": statistics.stdev(downloads) if repeats > 1 else 0,
        "upload_avg": sum(uploads)/repeats,
        "upload_std": statistics.stdev(uploads) if repeats > 1 else 0,
        "ping": st.results.ping
    }

def evaluate_stability(ping_std, jitter, packet_loss):
    if ping_std < 5 and jitter < 10 and packet_loss == 0:
        return "安定"
    elif ping_std < 10 and jitter < 20 and packet_loss < 1:
        return "普通"
    else:
        return "注意"

def main():
    print("=== ゲーム向け通信品質測定 ===\n")
    
    speed = test_speed()
    print(f"ダウンロード: {speed['download_avg']:.2f} Mbps ±{speed['download_std']:.2f}")
    print(f"アップロード: {speed['upload_avg']:.2f} Mbps ±{speed['upload_std']:.2f}")
    print(f"Ping（ISP経路）: {speed['ping']:.2f} ms\n")

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
