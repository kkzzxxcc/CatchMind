from socket import *
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from threading import Thread

class test2:
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

        self.initialize_socket(ip, 2600)
        self.user_name = name
        # 사용자 이름 전송
        self.client_socket.sendall(f"NICKNAME:{name}\n".encode('utf-8'))
        self.setup_main_ui()


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

        self.canvas = Canvas(main_frame, width=400, height=400, bg="white")
        self.canvas.pack(side=LEFT, padx=10, pady=10)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-1>", self.start_paint)

        chat_frame = Frame(main_frame)
        chat_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)

        Label(chat_frame, text=f'사용자 이름: {self.user_name}').pack(anchor=W)

        self.chat_transcript_area = ScrolledText(chat_frame, height=20, width=40, state='disabled')
        self.chat_transcript_area.pack(fill=BOTH, expand=True, pady=5)

        self.enter_text_widget = Entry(chat_frame, width=40)
        self.enter_text_widget.pack(fill=X, pady=5)
        self.enter_text_widget.bind("<Return>", self.send_chat)

        self.send_btn = Button(chat_frame, text='전송', command=self.send_chat)
        self.send_btn.pack(anchor=E, pady=5)

        self.last_x, self.last_y = None, None
        self.can_draw = False

    def send_chat(self, event=None):
        '''
        메시지를 서버로 전송하고 로컬에서도 메시지를 표시합니다.
        '''
        data = self.enter_text_widget.get()
        if data.strip():
            message = f"CHAT:{self.user_name}: {data}".encode('utf-8')
            print(f"[DEBUG] Sending message to server: {message.decode('utf-8')}")  # 디버그 로그 추가
            self.client_socket.send(message)
            self.chat_transcript_area.config(state='normal')
            self.chat_transcript_area.insert(END, f"{self.user_name}: {data}\n")
            self.chat_transcript_area.config(state='disabled')
            self.chat_transcript_area.yview(END)
            self.enter_text_widget.delete(0, END)

    def listen_thread(self):
        t = Thread(target=self.receive_message, args=(self.client_socket,))
        t.start()

    def receive_message(self, so):
        buffer = ""
        while True:
            try:
                buf = so.recv(1024).decode('utf-8')
                if not buf:
                    print("Server closed the connection.")
                    break
                buffer += buf
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    self.process_message(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
        so.close()

    def process_message(self, message):
        if message.startswith("CLEAR_CANVAS:"):
            # 모든 클라이언트에서 그림판 초기화
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

        elif message.startswith("NEW_ROUND:"):
            round_info = message.split(":", 1)[1]
            self.chat_transcript_area.config(state='normal')
            self.chat_transcript_area.insert(END, round_info + "\n")
            self.chat_transcript_area.config(state='disabled')
            self.chat_transcript_area.yview(END)
            self.can_draw = False


        elif message.startswith("SCORE_UPDATE:"):
            try:
                parts = message.split(":")
                client_name = parts[1]  # IP와 포트를 사용자 이름으로 사용
                score = parts[2]  # 점수
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"{client_name}님의 점수: {score}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
            except IndexError:
                print(f"[DEBUG] SCORE_UPDATE 메시지 파싱 오류: {message}")


        elif message.startswith("GAME_OVER:"):
            self.chat_transcript_area.config(state='normal')
            self.chat_transcript_area.insert(END, message + '\n')
            self.chat_transcript_area.config(state='disabled')
            self.chat_transcript_area.yview(END)

    def clear_canvas(self):
        '''
        그림판을 초기화합니다.
        '''
        self.canvas.delete("all")

    def start_paint(self, event):
        if self.can_draw:
            self.last_x, self.last_y = event.x, event.y

    def paint(self, event):
        if self.can_draw and self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill="black", width=2)
            draw_message = f"DRAW:{self.last_x}:{self.last_y}:{event.x}:{event.y}"
            self.client_socket.send(draw_message.encode('utf-8'))
            self.last_x, self.last_y = event.x, event.y


if __name__ == "__main__":
    client = test2()
    client.root.mainloop()