# 初期作成テスト

import speedtest

def test_internet_speed():
    print("=== インターネット速度測定 ===")
    print("測定中です…少々お待ちください。\n")

    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download() / 1_000_000
    upload_speed = st.upload() / 1_000_000
    ping = st.results.ping

    print(f"Ping: {ping:.2f} ms")
    print(f"ダウンロード速度: {download_speed:.2f} Mbps")
    print(f"アップロード速度: {upload_speed:.2f} Mbps")

if __name__ == "__main__":
    test_internet_speed()
