from socket import *
from threading import Thread
import random


class testServer2:
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

                Thread(target=self.receive_messages, args=(c_socket, ip, port)).start()
            except Exception as e:
                print(f"Accept 오류 발생: {e}")

    def start_new_round(self):
        if self.game_over or not self.clients:
            return

        # 제시어 선택 및 현재 그림 그리는 사람 설정
        self.current_word = random.choice(self.words)
        self.current_drawer_index %= len(self.clients)
        drawer_socket, ip, port = self.clients[self.current_drawer_index]

        # 모든 클라이언트에게 그림판 초기화 명령
        self.broadcast("CLEAR_CANVAS:\n")

        # 각 클라이언트에게 상태 전달
        for c_socket, _, _ in self.clients:
            if c_socket == drawer_socket:
                c_socket.sendall(f"YOUR_TURN:제시어는 '{self.current_word}'입니다.\n".encode('utf-8'))
            else:
                c_socket.sendall(f"NEW_ROUND:{ip}:{port}님이 그림을 그리고 있습니다.\n".encode('utf-8'))

        print(f"[DEBUG] 제시어 전달: {self.current_word} to {ip}:{port}")

    def receive_messages(self, c_socket, ip, port):
        while True:
            try:
                message = c_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break

                if message.startswith("DRAW:"):
                    if self.clients[self.current_drawer_index][0] == c_socket:
                        self.broadcast(message + "\n", c_socket)

                elif message.startswith("CHAT:"):
                    chat_message = message[5:].strip()
                    _, answer = chat_message.split(": ", 1)

                    if answer.lower() == self.current_word.lower() and c_socket != \
                            self.clients[self.current_drawer_index][0]:
                        self.scores[c_socket] += 1
                        client_name = self.get_client_name(c_socket)
                        self.broadcast(f"SCORE_UPDATE:{client_name}:{self.scores[c_socket]}\n")

                        if self.scores[c_socket] >= self.max_score:
                            self.broadcast(f"GAME_OVER:{client_name}님이 승리했습니다!\n")
                            self.game_over = True
                            self.s_sock.close()
                            break
                        else:
                            self.current_drawer_index += 1
                            self.start_new_round()
                    else:
                        self.broadcast(message + "\n", c_socket)

            except Exception as e:
                print(f"[DEBUG] Error receiving message from {ip}:{port}: {e}")
                break
        self.disconnect_client(c_socket, ip, port)

    def get_client_name(self, client_socket):
        '''
        클라이언트 소켓으로부터 사용자 이름을 반환
        '''
        for c_socket, ip, port in self.clients:
            if c_socket == client_socket:
                return f"{ip}:{port}"  # IP 대신 사용자 이름 매핑 가능
        return "Unknown"

    def broadcast(self, message, sender_socket=None):
        for c_socket, _, _ in self.clients:
            if c_socket != sender_socket:
                try:
                    c_socket.sendall(message.encode('utf-8'))
                except:
                    self.disconnect_client(c_socket, None, None)

    def disconnect_client(self, c_socket, ip, port):
        self.clients = [client for client in self.clients if client[0] != c_socket]
        if c_socket in self.client_names:
            del self.client_names[c_socket]
        if c_socket in self.scores:
            del self.scores[c_socket]
        c_socket.close()
        print(f"클라이언트 연결 해제: {ip}:{port}")

if __name__ == "__main__":
    server = testServer2(2600)