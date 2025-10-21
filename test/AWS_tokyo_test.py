# 東京のAWSサーバーとの通信テスト

import subprocess
import platform

def ping_host(host):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = subprocess.run(["ping", param, "4", host], capture_output=True, text=True)
    print(result.stdout)

ping_host("ec2.ap-northeast-1.amazonaws.com")
