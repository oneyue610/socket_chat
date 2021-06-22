# coding: utf-8
import time
from socket import *
from locust import TaskSet, task, between, Locust, events, User
import struct

HEADSIZE = 8


class SocketUser(User):
    # 目标地址
    host = "127.0.0.1"
    # 目标端口
    port = 1235
    # 等待时间, 用户连续的请求之间随机等待0.1~1s
    wait_time = between(0.1, 1)

    def __init__(self, *args, **kwargs):
        super(SocketUser, self).__init__(*args, **kwargs)
        self.client = socket(AF_INET, SOCK_STREAM)

    def on_start(self):
        self.client.connect((self.host, self.port))

    def on_stop(self):
        self.client.close()

    @task(100)  # 只有这个任务
    def sendHeartBeat(self):
        start_time = time.time()
        try:
            self.client.send(self.packdata(3, 'online?'))
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(request_type="3", name="SendMessage", response_time=total_time,
                                        response_length=0, exception=e)
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(request_type="3", name="SendMessage", response_time=total_time,
                                        response_length=0)

        start_time = time.time()
        try:
            data = self.client.recv(1024)
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(request_type="3", name="RecvMessage", response_time=total_time,
                                        response_length=0, exception=e)
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(request_type="3", name="RecvMessage", response_time=total_time,
                                        response_length=0)

    # 对发送内容进行分类和打包
    def packdata(self, type, data):
        bodylen = len(data.encode())
        header = [type, bodylen]
        headPack = struct.pack('!2I', *header)
        # !代表网络字节顺序NBO（Network Byte Order）,，2I代表2个unsigned int数据
        return headPack + data.encode()
    # 目前定义的消息类型有 0：约定指令 1：聊天消息 2：文件消息