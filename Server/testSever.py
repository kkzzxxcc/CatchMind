from socket import *
from threading import Thread
import random
import json


class testServer:
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
        self.accept_clients()

    def accept_clients(self):
        while len(self.clients) < 5:
            try:
                c_socket, (ip, port) = self.s_sock.accept()
                nickname = c_socket.recv(1024).decode('utf-8').strip().split("NICKNAME:")[1]
                self.clients.append((c_socket, ip, port))
                self.client_names[c_socket] = nickname
                self.scores[c_socket] = 0
                print(f"클라이언트 연결됨: {nickname} ({ip}:{port})")

                if len(self.clients) == 1:
                    self.start_new_round()

                self.broadcast_client_list()

                Thread(target=self.receive_messages, args=(c_socket, ip, port)).start()
            except Exception as e:
                print(f"Accept 오류 발생: {e}")

    def start_new_round(self):
        if self.game_over or not self.clients:
            return

        self.current_word = random.choice(self.words)
        self.current_drawer_index %= len(self.clients)
        drawer_socket, ip, port = self.clients[self.current_drawer_index]

        self.broadcast(json.dumps({"type": "CLEAR_CANVAS"}))

        for c_socket, _, _ in self.clients:
            if c_socket == drawer_socket:
                c_socket.sendall(json.dumps({"type": "YOUR_TURN", "word": self.current_word}).encode('utf-8'))
            else:
                drawer_name = self.client_names.get(drawer_socket, f"{ip}:{port}")
                c_socket.sendall(json.dumps({"type": "NEW_ROUND", "drawer": drawer_name}).encode('utf-8'))

        print(f"[DEBUG] 제시어 전달: {self.current_word} to {ip}:{port}")

    def receive_messages(self, c_socket, ip, port):
        while True:
            try:
                message = c_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break

                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    print(f"[DEBUG] Parsed JSON message: {data}")  # JSON 메시지 로그

                    if message_type == "CLEAR_CANVAS_REQUEST":
                        if c_socket == self.clients[self.current_drawer_index][0]:
                            self.broadcast(json.dumps({"type": "CLEAR_CANVAS"}))

                    elif message_type == "DRAW":
                        if self.clients[self.current_drawer_index][0] == c_socket:
                            self.broadcast(message, sender_socket=c_socket)

                    elif message_type == "CHAT":
                        username = data.get("username")
                        chat_message = data.get("message")
                        self.broadcast(message)

                        if chat_message.lower() == self.current_word.lower() and c_socket != \
                                self.clients[self.current_drawer_index][0]:
                            self.scores[c_socket] += 1
                            client_name = self.client_names.get(c_socket, "Unknown")
                            self.broadcast(json.dumps({"type": "SCORE_UPDATE", "username": client_name,
                                                       "score": self.scores[c_socket]}))

                            if self.scores[c_socket] >= self.max_score:
                                self.broadcast(json.dumps({"type": "GAME_OVER", "winner": client_name}))
                                self.game_over = True
                                self.s_sock.close()
                                break
                            else:
                                self.current_drawer_index += 1
                                self.start_new_round()
                        else:
                            self.broadcast(message)

                except json.JSONDecodeError:
                    print(f"[DEBUG] Invalid message format: {message}")

            except Exception as e:
                print(f"[DEBUG] Error receiving message from {ip}:{port}: {e}")
                break
        self.disconnect_client(c_socket, ip, port)

    def broadcast(self, message, sender_socket=None):
        for c_socket, _, _ in self.clients:
            if c_socket != sender_socket:
                try:
                    c_socket.sendall(message.encode('utf-8'))
                except:
                    self.disconnect_client(c_socket, None, None)

    def broadcast_client_list(self):
        client_list = [self.client_names[c] for c in self.client_names]
        self.broadcast(json.dumps({"type": "CLIENT_LIST", "clients": client_list}))

    def disconnect_client(self, c_socket, ip, port):
        self.clients = [client for client in self.clients if client[0] != c_socket]
        if c_socket in self.client_names:
            del self.client_names[c_socket]
        if c_socket in self.scores:
            del self.scores[c_socket]
        c_socket.close()
        print(f"클라이언트 연결 해제: {ip}:{port}")


if __name__ == "__main__":
    server = testServer(2600)
