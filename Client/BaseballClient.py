import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
from tkinter import simpledialog

def receive_messages():
    while True:
        try:
            message = client_socket.recv(1024).decode()
            chat_area.config(state=tk.NORMAL)
            chat_area.insert(tk.END, message + '\n')
            chat_area.config(state=tk.DISABLED)
            chat_area.see(tk.END)
        except:
            print("오류가 발생했습니다. 종료합니다...")
            client_socket.close()
            break

def send_message(event=None):
    message = input_area.get()
    input_area.delete(0, tk.END)
    client_socket.send(message.encode())
    if message == "EXIT":
        client_socket.close()
        app.quit()

def start_game():
    client_socket.send("START_GAME".encode())

def send_guess():
    guess = guess_input.get()
    guess_input.delete(0, tk.END)
    client_socket.send(f"GUESS:{guess}".encode())

# Connect to server
connection_dialog = tk.Tk()
connection_dialog.withdraw()

HOST = simpledialog.askstring("연결 설정", "서버 IP를 입력하세요:")
PORT = simpledialog.askinteger("연결 설정", "서버 포트를 입력하세요:")
USERNAME = simpledialog.askstring("사용자 이름", "사용자 이름을 입력하세요:")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
client_socket.send(f"USERNAME:{USERNAME}".encode())

# GUI setup
app = tk.Tk()
app.title("숫자 야구 게임")

# Chat area
chat_frame = tk.Frame(app)
chat_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED, height=15, width=50)
chat_area.pack(padx=10, pady=10)
chat_frame.pack(side=tk.LEFT, padx=10, pady=10)

# Input area
input_frame = tk.Frame(app)
input_area = tk.Entry(input_frame, width=40)
input_area.pack(side=tk.LEFT, padx=10)
input_area.bind("<Return>", send_message)

send_button = tk.Button(input_frame, text="전송", command=send_message)
send_button.pack(side=tk.RIGHT, padx=10)

input_frame.pack(side=tk.LEFT, padx=10, pady=10)

# Game area
game_frame = tk.Frame(app)
start_button = tk.Button(game_frame, text="게임 시작", command=start_game)
start_button.pack(pady=5)

guess_label = tk.Label(game_frame, text="숫자를 입력하세요:")
guess_label.pack()

guess_input = tk.Entry(game_frame)
guess_input.pack(pady=5)

submit_guess_button = tk.Button(game_frame, text="추측 제출", command=send_guess)
submit_guess_button.pack(pady=5)

game_frame.pack(side=tk.RIGHT, padx=10, pady=10)

# Start receiving thread
receive_thread = threading.Thread(target=receive_messages)
receive_thread.daemon = True
receive_thread.start()

app.mainloop()
