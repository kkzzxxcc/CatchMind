from socket import *
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from threading import Thread
import json


class test:
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

        canvas_frame = Frame(main_frame)
        canvas_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)

        self.clear_button = Button(canvas_frame, text="그림판 지우기", command=self.request_clear_canvas, state=DISABLED)
        self.clear_button.pack(anchor=NW, pady=5)

        self.canvas = Canvas(canvas_frame, width=400, height=400, bg="white")
        self.canvas.pack(fill=BOTH, expand=True)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-1>", self.start_paint)

        chat_frame = Frame(main_frame)
        chat_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)

        Label(chat_frame, text=f'사용자 이름: {self.user_name}').pack(anchor=W)

        self.chat_transcript_area = ScrolledText(chat_frame, height=20, width=40, state='disabled')
        self.chat_transcript_area.pack(fill=BOTH, expand=True, pady=5)

        self.client_list_area = ScrolledText(chat_frame, height=10, width=20, state='disabled')
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
            message = {
                "type": "CHAT",
                "username": self.user_name,
                "message": data
            }
            print(f"[DEBUG] Sending message to server: {message}")  # 로그 추가
            self.client_socket.sendall(json.dumps(message).encode('utf-8'))

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
        try:
            print(f"[DEBUG] Received raw message: {message}")  # 로그 추가
            data = json.loads(message)
            print(f"[DEBUG] Parsed JSON message: {data}")  # JSON 메시지 로그
            message_type = data.get("type")

            if message_type == "CLEAR_CANVAS":
                self.clear_canvas()

            elif message_type == "DRAW":
                x1 = data.get("x1")
                y1 = data.get("y1")
                x2 = data.get("x2")
                y2 = data.get("y2")
                self.canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

            elif message_type == "CHAT":
                username = data.get("username")
                chat_message = data.get("message")
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"{username}: {chat_message}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)

            elif message_type == "YOUR_TURN":
                word = data.get("word")
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"당신의 차례입니다! 제시어: {word}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
                self.can_draw = True
                self.clear_button.config(state=NORMAL)

            elif message_type == "NEW_ROUND":
                drawer = data.get("drawer")
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"{drawer}님이 그림을 그리고 있습니다.\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)
                self.can_draw = False
                self.clear_button.config(state=DISABLED)

            elif message_type == "SCORE_UPDATE":
                username = data.get("username")
                score = data.get("score")
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"{username}님의 점수: {score}\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)

            elif message_type == "GAME_OVER":
                winner = data.get("winner")
                self.chat_transcript_area.config(state='normal')
                self.chat_transcript_area.insert(END, f"게임 종료! {winner}님이 승리했습니다!\n")
                self.chat_transcript_area.config(state='disabled')
                self.chat_transcript_area.yview(END)

            elif message_type == "CLIENT_LIST":
                clients = data.get("clients", [])
                self.client_list_area.config(state='normal')
                self.client_list_area.delete(1.0, END)
                self.client_list_area.insert(END, "\n".join(clients) + '\n')
                self.client_list_area.config(state='disabled')

        except json.JSONDecodeError:
            print(f"[DEBUG] Invalid message format: {message}")

    def clear_canvas(self):
        self.canvas.delete("all")

    def start_paint(self, event):
        if self.can_draw:
            self.last_x, self.last_y = event.x, event.y

    def paint(self, event):
        if self.can_draw and self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill="black", width=2)
            draw_message = {
                "type": "DRAW",
                "x1": self.last_x,
                "y1": self.last_y,
                "x2": event.x,
                "y2": event.y
            }
            self.client_socket.sendall(json.dumps(draw_message).encode('utf-8'))
            self.last_x, self.last_y = event.x, event.y

    def request_clear_canvas(self):
        if self.can_draw:
            clear_message = {
                "type": "CLEAR_CANVAS_REQUEST"
            }
            self.client_socket.sendall(json.dumps(clear_message).encode('utf-8'))


if __name__ == "__main__":
    client = test()
    client.root.mainloop()
