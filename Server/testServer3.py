from socket import *
from threading import Thread
import random


class testServer3:
    def __init__(self, port=2600):
        self.clients = []  # 연결된 클라이언트 소켓 리스트
        self.client_names = {}  # 클라이언트 소켓과 사용자 이름 매핑
        self.s_sock = socket(AF_INET, SOCK_STREAM)
        self.s_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.s_sock.bind(('', port))
        self.s_sock.listen(5)

        self.scores = {}  # 클라이언트 점수 관리
        self.current_drawer_index = 0
        self.words = ["apple", "banana", "car", "dog", "elephant"]
        self.current_word = None
        self.max_score = 3
        self.game_over = False

        print(f"서버가 {port} 포트에서 시작되었습니다.")
        self.accept_clients_thread = Thread(target=self.accept_clients)
        self.accept_clients_thread.start()

    def accept_clients(self):
        while not self.game_over:  # 게임이 종료되면 루프를 종료
            try:
                c_socket, (ip, port) = self.s_sock.accept()
                try:
                    nickname = c_socket.recv(1024).decode('utf-8').strip().split("NICKNAME:")[1]
                except (IndexError, UnicodeDecodeError):
                    print(f"[DEBUG] 잘못된 닉네임 데이터를 수신했습니다. {ip}:{port}")
                    c_socket.close()
                    continue

                self.clients.append((c_socket, ip, port))
                self.client_names[c_socket] = nickname
                self.scores[c_socket] = 0
                print(f"클라이언트 연결됨: {nickname} ({ip}:{port})")

                if len(self.clients) == 1:
                    self.start_new_round()

                # 클라이언트 리스트 브로드캐스트
                self.broadcast_client_list()

                Thread(target=self.receive_messages, args=(c_socket, ip, port)).start()
            except Exception as e:
                if not self.game_over:  # 소켓이 닫히기 전의 오류만 출력
                    print(f"Accept 오류 발생: {e}")

    def start_new_round(self):
        if self.game_over or not self.clients:
            return

        self.current_word = random.choice(self.words)
        self.current_drawer_index %= len(self.clients)
        drawer_socket, ip, port = self.clients[self.current_drawer_index]

        self.broadcast("CLEAR_CANVAS:\n")

        for c_socket, _, _ in self.clients:
            if c_socket == drawer_socket:
                c_socket.sendall(f"YOUR_TURN:제시어는 '{self.current_word}'입니다.\n".encode('utf-8'))
            else:
                drawer_name = self.client_names.get(drawer_socket, f"{ip}:{port}")
                c_socket.sendall(f"NEW_ROUND:{drawer_name}님이 그림을 그리고 있습니다.\n".encode('utf-8'))

        print(f"[DEBUG] 제시어 전달: {self.current_word} to {ip}:{port}")

    def receive_messages(self, c_socket, ip, port):
        while True:
            try:
                message = c_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break

                if message.startswith("CLEAR_CANVAS_REQUEST:"):
                    if c_socket == self.clients[self.current_drawer_index][0]:
                        self.broadcast("CLEAR_CANVAS:\n")

                elif message.startswith("DRAW:"):
                    if self.clients[self.current_drawer_index][0] == c_socket:
                        self.broadcast(message + "\n", c_socket)

                elif message.startswith("CHAT:"):
                    chat_message = message[5:].strip()
                    try:
                        _, answer = chat_message.split(": ", 1)
                    except ValueError:
                        self.broadcast(message + "\n", c_socket)
                        continue

                    if answer.lower() == self.current_word.lower() and c_socket != \
                            self.clients[self.current_drawer_index][0]:
                        self.scores[c_socket] += 1
                        client_name = self.client_names.get(c_socket, "Unknown")
                        self.broadcast(f"SCORE_UPDATE:{client_name}:{self.scores[c_socket]}\n")

                        self.broadcast_client_list()

                        if self.scores[c_socket] >= self.max_score:
                            self.broadcast(f"GAME_OVER:{client_name}님이 승리했습니다!\n")
                            self.game_over = True
                            self.shutdown_server()  # 서버 종료
                            return
                        else:
                            self.current_drawer_index += 1
                            self.start_new_round()
                    else:
                        self.broadcast(message + "\n", c_socket)

            except Exception as e:
                print(f"[DEBUG] 메시지 수신 오류 {ip}:{port}: {e}")
                break

        self.disconnect_client(c_socket, ip, port)

    def broadcast(self, message, sender_socket=None):
        for c_socket, _, _ in self.clients:
            if c_socket != sender_socket:
                try:
                    c_socket.sendall(message.encode('utf-8'))
                except Exception as e:
                    print(f"[DEBUG] 브로드캐스트 오류: {e}")
                    self.disconnect_client(c_socket, None, None)

    def disconnect_client(self, c_socket, ip, port):
        self.clients = [client for client in self.clients if client[0] != c_socket]
        if c_socket in self.client_names:
            del self.client_names[c_socket]
        if c_socket in self.scores:
            del self.scores[c_socket]
        try:
            c_socket.close()
        except Exception as e:
            print(f"[DEBUG] 클라이언트 소켓 닫기 오류: {e}")
        print(f"클라이언트 연결 해제: {ip}:{port}")

    def broadcast_client_list(self):
        try:
            client_list = [f"{self.client_names[c]} 점수: {self.scores[c]}" for c in self.client_names]
            message = "CLIENT_LIST:" + ",".join(client_list) + "\n"
            print(f"[DEBUG] Broadcasting client list: {message.strip()}")
            self.broadcast(message)
        except Exception as e:
            print(f"[DEBUG] 클라이언트 리스트 브로드캐스트 오류: {e}")

    def shutdown_server(self):
        print("게임이 종료되었습니다. 서버를 종료합니다.")
        self.s_sock.close()
        for c_socket, _, _ in self.clients:
            try:
                c_socket.close()
            except Exception as e:
                print(f"[DEBUG] 클라이언트 소켓 종료 오류: {e}")
        self.clients.clear()

if __name__ == "__main__":
    server = testServer3(2600)
