import subprocess
import platform
import re
import speedtest

# 測定するサーバー
GAME_SERVERS = {
    "AWS Tokyo": "ec2.ap-northeast-1.amazonaws.com",
    "AWS Singapore": "ec2.ap-southeast-1.amazonaws.com"
}

def ping_host(host, count=4):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = subprocess.run(["ping", param, str(count), host],
                            capture_output=True, text=True)
    output = result.stdout
    # Ping値の抽出
    times = re.findall(r'time[=<]([0-9.]+) ms', output)
    times = [float(t) for t in times]
    packet_loss = re.search(r'(\d+)% packet loss', output)
    packet_loss = int(packet_loss.group(1)) if packet_loss else 0
    avg = sum(times)/len(times) if times else 0
    jitter = max(times)-min(times) if times else 0
    return {"avg_ping": avg, "jitter": jitter, "packet_loss": packet_loss}

def test_speed():
    print("=== インターネット速度測定 ===")
    st = speedtest.Speedtest()
    st.get_best_server()
    download = st.download() / 1_000_000
    upload = st.upload() / 1_000_000
    ping = st.results.ping
    return {"download": download, "upload": upload, "ping": ping}

def main():
    print("測定中…少々お待ちください。\n")

    speed = test_speed()
    print(f"ダウンロード速度: {speed['download']:.2f} Mbps")
    print(f"アップロード速度: {speed['upload']:.2f} Mbps")
    print(f"Ping: {speed['ping']:.2f} ms\n")

    print("ゲームサーバーPing測定:")
    for name, host in GAME_SERVERS.items():
        result = ping_host(host)
        print(f"{name} - 平均Ping: {result['avg_ping']:.2f} ms, "
              f"ジッター: {result['jitter']:.2f} ms, "
              f"パケットロス: {result['packet_loss']}%")

if __name__ == "__main__":
    main()
