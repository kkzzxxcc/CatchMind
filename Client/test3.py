from socket import *
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from threading import Thread

class test3:
    client_socket = None

    def __init__(self):
        self.root = Tk()
        self.root.title("CatchMind - Login")
        self.setup_login_ui()

    def setup_login_ui(self):
        login_frame = Frame(self.root)
        login_frame.pack(pady=20, padx=20)

        Label(login_frame, text="서버 IP:").grid(row=0, column=0, pady=5)
        self.ip_entry = Entry(login_frame, width=20)
        self.ip_entry.grid(row=0, column=1, pady=5)
        self.ip_entry.insert(0, "127.0.0.1")

        Label(login_frame, text="사용자 이름:").grid(row=1, column=0, pady=5)
        self.name_entry = Entry(login_frame, width=20)
        self.name_entry.grid(row=1, column=1, pady=5)

        Button(login_frame, text="시작", command=self.start_game).grid(row=2, column=0, columnspan=2, pady=10)

    def start_game(self):
        ip = self.ip_entry.get()
        name = self.name_entry.get().strip()

        if not ip or not name:
            print("IP와 이름을 모두 입력하세요!")
            return

        try:
            self.initialize_socket(ip, 2600)
            self.user_name = name
            # 사용자 이름 전송
            self.client_socket.sendall(f"NICKNAME:{name}\n".encode('utf-8'))
            self.setup_main_ui()
        except Exception as e:
            print(f"서버 연결 오류: {e}")

    def initialize_socket(self, ip, port):
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((ip, port))
        print(f"Connected to server at {ip}:{port}")

    def setup_main_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title("CatchMind")
        self.initialize_gui()
        self.listen_thread()

    def initialize_gui(self):
        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True)

        # 좌측 그림판 영역
        canvas_frame = Frame(main_frame)
        canvas_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)

        # "그림판 지우기" 버튼 추가
        self.clear_button = Button(canvas_frame, text="그림판 지우기", command=self.request_clear_canvas, state=DISABLED)
        self.clear_button.pack(anchor=NW, pady=5)

        # 그림판
        self.canvas = Canvas(canvas_frame, width=400, height=400, bg="white")
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-1>", self.start_paint)

        # 우측 채팅 및 기타 정보 영역
        chat_frame = Frame(main_frame)
        chat_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)

        Label(chat_frame, text=f'사용자 이름: {self.user_name}').pack(anchor=W)

        self.chat_transcript_area = ScrolledText(chat_frame, height=20, width=40, state='disabled')
        self.chat_transcript_area.pack(fill=BOTH, expand=True, pady=5)

        Label(chat_frame, text='접속 클라이언트:').pack(anchor=W)
        self.client_list_area = ScrolledText(chat_frame, height=5, width=20, state='disabled')
        self.client_list_area.pack(fill=BOTH, expand=False, pady=5)

        self.enter_text_widget = Entry(chat_frame, width=40)
        self.enter_text_widget.pack(fill=X, pady=5)
        self.enter_text_widget.bind("<Return>", self.send_chat)

        self.send_btn = Button(chat_frame, text='전송', command=self.send_chat)
        self.send_btn.pack(anchor=E, pady=5)

        self.last_x, self.last_y = None, None
        self.can_draw = False

    def send_chat(self, event=None):
        data = self.enter_text_widget.get()
        if data.strip():
            try:
                message = f"CHAT:{self.user_name}: {data}".encode('utf-8')
                self.client_socket.send(message)
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"{self.user_name}: {data}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
                self.enter_text_widget.delete(0, END)
            except Exception as e:
                print(f"메시지 전송 오류: {e}")

    def listen_thread(self):
        t = Thread(target=self.receive_message, args=(self.client_socket,))
        t.daemon = True
        t.start()

    def receive_message(self, so):
        buffer = ""
        while True:
            try:
                buf = so.recv(1024).decode('utf-8')
                if not buf:
                    print("서버와 연결이 끊어졌습니다.")
                    break
                buffer += buf
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    self.process_message(message)
            except Exception as e:
                print(f"서버 메시지 수신 오류: {e}")
                break
        so.close()

    def request_clear_canvas(self):
        if self.can_draw:
            try:
                self.client_socket.sendall("CLEAR_CANVAS_REQUEST:\n".encode('utf-8'))
            except Exception as e:
                print(f"그림판 지우기 요청 오류: {e}")

    def process_message(self, message):
        try:
            if message.startswith("CLEAR_CANVAS:"):
                self.clear_canvas()
            elif message.startswith("DRAW:"):
                _, x1, y1, x2, y2 = message.split(":")
                self.canvas.create_line(float(x1), float(y1), float(x2), float(y2), fill="black", width=2)
            elif message.startswith("CHAT:"):
                chat_message = message.split(":", 1)[1]
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, chat_message + '\n')
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
            elif message.startswith("YOUR_TURN:"):
                word = message.split(":", 1)[1]
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"당신의 차례입니다! 제시어: {word}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
                self.can_draw = True
                self.clear_button.config(state=NORMAL)
            elif message.startswith("NEW_ROUND:"):
                round_info = message.split(":", 1)[1]
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, round_info + "\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
                self.can_draw = False
                self.clear_button.config(state=DISABLED)
            elif message.startswith("SCORE_UPDATE:"):
                parts = message.split(":")
                client_name = parts[1]
                score = parts[2]
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"{client_name}님의 점수: {score}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
            elif message.startswith("GAME_OVER:"):
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, message + '\n')
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
            elif message.startswith("CLIENT_LIST:"):
                try:
                    clients = message.split(":", 1)[1].split(",")
                    print(f"[DEBUG] Received client list: {clients}")  # 디버그 로그 추가
                    self.client_list_area.config(state='normal')
                    self.client_list_area.delete(1.0, END)  # 기존 리스트 삭제
                    for client_info in clients:
                        self.client_list_area.insert(END, f"{client_info}\n")
                    self.client_list_area.config(state='disabled')
                except Exception as e:
                    print(f"[DEBUG] Error updating client list: {e}")

        except Exception as e:
            print(f"메시지 처리 오류: {e}")

    def clear_canvas(self):
        self.canvas.delete("all")

    def start_paint(self, event):
        if self.can_draw:
            self.last_x, self.last_y = event.x, event.y

    def paint(self, event):
        if self.can_draw and self.last_x and self.last_y:
            try:
                self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill="black", width=2)
                draw_message = f"DRAW:{self.last_x}:{self.last_y}:{event.x}:{event.y}"
                self.client_socket.send(draw_message.encode('utf-8'))
                self.last_x, self.last_y = event.x, event.y
            except Exception as e:
                print(f"그림 전송 오류: {e}")

if __name__ == "__main__":
    client = test3()
    client.root.mainloop()
