import sys, csv, os, threading, time, traceback
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, 
    QProgressBar, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QMovie, QTextCursor
import speedtest
from ping3 import ping

# ---------------------- 設定 ----------------------
GAME_SERVERS = {
    "AWS Tokyo": "ec2.ap-northeast-1.amazonaws.com",
    "AWS Singapore": "ec2.ap-southeast-1.amazonaws.com"
}
TIMEOUT_SPEEDTEST = 30
PING_COUNT = 5
CSV_SAVE_PATH = "speedtest_history.csv"
SPINNER_PATH = os.path.join(os.path.dirname(__file__), "image", "loading_spinner.gif")

# ---------------------- シグナルクラス ----------------------
class WorkerSignals(QObject):
    update_status = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    update_text = pyqtSignal(str, str)
    finished = pyqtSignal()

# ---------------------- 測定スレッド ----------------------
class TestThread(threading.Thread):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals

    def safe_speedtest(self):
        result = {}
        def worker():
            try:
                st = speedtest.Speedtest()
                st.get_best_server()
                result["download"] = st.download() / 1_000_000
                result["upload"] = st.upload() / 1_000_000
                result["ping"] = st.results.ping
            except Exception as e:
                result["error"] = f"{e}\n{traceback.format_exc()}"
        t = threading.Thread(target=worker)
        t.start()
        t.join(TIMEOUT_SPEEDTEST)
        if t.is_alive():
            self.signals.update_text.emit("速度測定タイムアウト\n", "red")
            return None
        if "error" in result:
            self.signals.update_text.emit(f"速度測定エラー:\n{result['error']}\n", "red")
            return None
        return result

    def safe_ping(self, host):
        pings=[]
        for _ in range(PING_COUNT):
            try:
                r = ping(host, timeout=2)
                pings.append(r*1000 if r is not None else None)
            except Exception as e:
                pings.append(None)
                self.signals.update_text.emit(f"{host} Ping例外: {e}\n", "red")
        avg_ping = sum([p for p in pings if p is not None])/len([p for p in pings if p is not None]) if any(p is not None for p in pings) else None
        packet_loss = sum([1 for p in pings if p is None])/len(pings)*100
        stability = "安定" if avg_ping is not None and packet_loss==0 else "注意"
        return {"avg_ping": avg_ping, "packet_loss": packet_loss, "stability": stability}

    def save_csv(self, speed, ping_results):
        header = ["日時","ダウンロード","アップロード","ISP-Ping"] + \
                 [f"{name}-平均Ping" for name in GAME_SERVERS.keys()] + \
                 [f"{name}-パケロス" for name in GAME_SERVERS.keys()] + \
                 [f"{name}-安定性" for name in GAME_SERVERS.keys()]
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [now]
        if speed:
            row += [speed["download"], speed["upload"], speed["ping"]]
        else:
            row += ["N/A"]*3
        for name in GAME_SERVERS.keys():
            r = ping_results.get(name)
            if r:
                row += [r["avg_ping"] if r['avg_ping'] is not None else "N/A",
                        r["packet_loss"] if r['packet_loss'] is not None else "N/A",
                        r["stability"]]
            else:
                row += ["N/A","N/A","失敗"]
        file_exists = os.path.isfile(CSV_SAVE_PATH)
        with open(CSV_SAVE_PATH, "a", newline="") as f:
            writer=csv.writer(f)
            if not file_exists:
                writer.writerow(header)
            writer.writerow(row)

    def run(self):
        current_progress = 0
        self.signals.update_progress.emit(current_progress)

        # ---- 速度測定 ----
        self.signals.update_status.emit("速度測定中")
        speed_result={}
        t_speed = threading.Thread(target=lambda: speed_result.update({"data": self.safe_speedtest()}))
        t_speed.start()
        while t_speed.is_alive():
            current_progress = min(current_progress+1,50)
            self.signals.update_progress.emit(current_progress)
            time.sleep(0.05)
        t_speed.join()
        self.signals.update_progress.emit(50)

        # ---- ゲームサーバーPing ----
        self.signals.update_status.emit("ゲームサーバーPing中")
        ping_results={}
        ping_threads=[]
        for name, host in GAME_SERVERS.items():
            t = threading.Thread(target=lambda n=name, h=host: ping_results.update({n:self.safe_ping(h)}))
            ping_threads.append(t)
            t.start()
        while any(t.is_alive() for t in ping_threads):
            current_progress = min(current_progress+1,90)
            self.signals.update_progress.emit(current_progress)
            time.sleep(0.05)
        for t in ping_threads: t.join()
        self.signals.update_progress.emit(90)

        # ---- 結果表示 ----
        s = speed_result.get("data")
        if s:
            self.signals.update_text.emit(
                f"=== インターネット速度 ===\n"
                f"ダウンロード: {s['download']:.2f} Mbps\n"
                f"アップロード: {s['upload']:.2f} Mbps\n"
                f"Ping: {s['ping']:.2f} ms\n\n","black")

        self.signals.update_text.emit("=== ゲームサーバーPing ===\n","black")
        for name in GAME_SERVERS.keys():
            r=ping_results.get(name)
            if r:
                avg_ping = f"{r['avg_ping']:.2f} ms" if r['avg_ping'] is not None else "N/A"
                packet_loss = f"{r['packet_loss']:.1f}%" if r['packet_loss'] is not None else "N/A"
                stability = r['stability']
                color = "black" if stability == "安定" else "red"
                self.signals.update_text.emit(f"{name} 平均Ping: {avg_ping} パケロス: {packet_loss} 安定性: {stability}\n", color)
            else:
                self.signals.update_text.emit(f"{name} Ping失敗\n", "red")

        for i in range(91,101):
            self.signals.update_progress.emit(i)
            time.sleep(0.02)

        self.save_csv(s,ping_results)
        self.signals.update_status.emit("測定完了！")
        self.signals.finished.emit()

# ---------------------- GUI ----------------------
class SpeedTestApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ゲーム向け通信品質測定（スピナー自動リサイズ版）")
        self.setGeometry(100,100,650,300)
        self.setMinimumSize(600,300)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        # --- 上部ボタン ---
        self.btn_test = QPushButton("測定開始")
        self.btn_test.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.btn_test)

        # --- プログレスバー ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.progress_bar)

        # --- 結果表示部分 ---
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.text_area)

        # --- スピナー（結果表示オーバーレイ） ---
        self.spinner_label = QLabel(self.text_area)
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.setStyleSheet("background: rgba(255,255,255,150);")
        self.spinner_movie = QMovie(SPINNER_PATH)
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.hide()

        # --- シグナル ---
        self.signals = WorkerSignals()
        self.signals.update_status.connect(self.update_status)
        self.signals.update_progress.connect(self.progress_bar.setValue)
        self.signals.update_text.connect(self.append_text)
        self.signals.finished.connect(self.on_finished)

        self.btn_test.clicked.connect(self.start_test)
        self.text_area.resizeEvent = self.on_text_resize

    # スピナー自動リサイズ対応
    def on_text_resize(self, event):
        self.spinner_label.setGeometry(0,0,self.text_area.width(),self.text_area.height())
        if self.spinner_movie:
            self.spinner_movie.setScaledSize(self.spinner_label.size())
        QTextEdit.resizeEvent(self.text_area, event)

    def append_text(self,text,color="black"):
        self.text_area.append(f'<span style="color:{color}">{text}</span>')
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)

    def start_test(self):
        self.text_area.clear()
        self.spinner_label.show()
        self.spinner_movie.start()
        self.progress_bar.setValue(0)
        self.btn_test.setEnabled(False)
        self.btn_test.setText("測定中")
        self.thread = TestThread(self.signals)
        self.thread.start()

    def on_finished(self):
        self.spinner_movie.stop()
        self.spinner_label.hide()
        self.btn_test.setEnabled(True)
        self.btn_test.setText("もう一度測定する")

    def update_status(self,text):
        if "測定中" in text:
            self.btn_test.setText(text)

# ---------------------- 実行 ----------------------
if __name__=="__main__":
    app=QApplication(sys.argv)
    window=SpeedTestApp()
    window.show()
    sys.exit(app.exec())
