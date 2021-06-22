# encoding: utf-8
import socket
from threading import Thread
import time
import tkinter as tk
import tkinter.messagebox
import os, sys
from threading import Thread
import inspect
import ctypes
import struct
import operator

HEADERSIZE = 8

class Server(object):
    # 初始方法
    def __init__(self):
        # 创建服务器文件夹
        if not os.path.exists('serverfiles'):
            os.mkdir('serverfiles')
        #将工作目录换到files文件夹下
        os.chdir('serverfiles')
        # 所有的客户端，列表存储client的socket四元组
        self.clients = []
        # 用户的name和ip，集合内部元素为键值对，socket对应id
        self.clients_name_ip = {}
        # 用户的在线状态
        self.clients_ip_online = {}
        # 用户的tcp状态
        self.clients_ip_tcp = {}
        # 自动获取ip
        hostname = socket.gethostname()
        iplt = socket.gethostbyname_ex(hostname)
        self.serverip = iplt[2][2]
        # port
        self.serverport = 1235
        # 服务器控制界面
        self.ui()

    def ui(self):
        self.window = tk.Tk()
        self.window.title("服务端后台")
        self.window.geometry('500x530+700+200')
        # ip展示
        tk.Label(self.window, text='IP: '+self.serverip).place(x=50, y=30)
        # 端口号展示
        tk.Label(self.window, text='port: '+str(self.serverport)).place(x=50,y=60)
        # 聊天室后台
        self.memberlist = tk.Text(self.window, width=55, height=20)
        self.memberlist.place(x=50, y=100)
        # 开始按钮
        stbtn = tk.Button(self.window, text='start', command=self.start).place(x=50, y=400)
        # 关闭按钮
        qtbtn = tk.Button(self.window,text='destroy', command=self.exitprogram).place(x=385, y=400)
        self.window.mainloop()

    def start(self):
        # 建立欢迎套接字的进程
        self.t1 = Thread(target=self.svsocket)
        self.t1.start()

    def exitprogram(self):
        for c in self.clients:
            c.send(self.packdata(0, '服务器已经正常关闭'))
            c.close()
        os._exit(0)    # 在子进程中通过os._exit关闭整个进程
         # 服务端退出

    def svsocket(self):
        # 创建TCP欢迎套接字
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 本地ip和端口号
        self.local_addr = ("127.0.0.1", 1235)
        # 绑定本地ip
        self.server_socket.bind(self.local_addr)
        self.server_socket.listen(1024)
        self.memberlist.insert('end', "服务器启动成功，等待客户连接......\n")
        self.get_conn()
        # 监听客户端与服务器连接

    def get_conn(self):
        while True:
            # 给客户端分配一个新的socket，获取客户端的ip地址
            new_socket, client_address = self.server_socket.accept()
            # 连接的所有用户添加到服务器的用户列表里面
            self.clients.append(new_socket)
            # 用户出生
            self.clients_ip_online[client_address]=0
            self.clients_ip_tcp[client_address]=0
            # 服务器启动多个线程，处理每一个客户端的消息
            Thread(target=self.stream_process, args=(new_socket, self.clients, self.clients_name_ip, client_address)).start()
    #        Thread(target=self.send_heart, args=(new_socket,self.clients,self.clients_name_ip,client_address)).start()
    '''
    # 通过心跳包检测用户是否异常退出
    def send_heart(self,new_socket, clients, clients_name_ip, client_address):
        while True:
            while (self.clients_ip_tcp[client_address]== 1):
                continue
            try:
                new_socket.send(self.packdata(3, 'online?'))
            except:
                self.close_socket(new_socket, client_address)
                break
            self.clients_ip_online[client_address] += 1
            if self.clients_ip_online[client_address] > 3:
                self.close_socket(new_socket, client_address)
                break
            time.sleep(2)
    '''

    def stream_process(self, new_socket, clients, clients_name_ip, client_address):
        databuffer = bytes()
        name = ''
        while True:
            try:
                data = new_socket.recv(1024)
            except:
                break
            if data:
                # 将数据存入缓冲区， 类似于push数据
                databuffer += data
            # databuffer信息大于包头的长度时
            while len(databuffer) > HEADERSIZE:
                # 拆包databuffer中的包头
                headPack = struct.unpack('!2I', databuffer[:HEADERSIZE])
                bodysize = headPack[1]
                # 小于包的长度时返回继续接收
                if len(databuffer) < HEADERSIZE + bodysize:
                    break
                body = databuffer[HEADERSIZE:HEADERSIZE+bodysize].decode()
                # 数据处理
                if(headPack[0]==10): # 10是名字流类型
                    name = body
                    # 将昵称和ip进行绑定
                    self.clients_name_ip[client_address] = name
                    # 广播新用户加入的消息
                    datatemp= self.clients_name_ip[client_address] + " " + time.strftime("%x") + "加入聊天室" + "\n"
                    for c in clients:
                        c.send(self.packdata(0,datatemp))
                        self.memberlist.insert('end', client_address)
                        self.memberlist.insert('end', '  ' + self.clients_name_ip[client_address] + " " + time.strftime(
                            "%x") + "加入聊天室" + '\n')
                elif (headPack[0] == 0):
                    if(body == 'agreement_upload'):
                        self.recv_file(new_socket, name, client_address)
                    elif(body == 'agreement_download'):
                        self.send_file(new_socket, name,client_address)
                    elif(body == 'agreement_file_list'):
                        self.return_file_list(new_socket, name,client_address)
                    elif(body == 'agreement_quit'):
                        self.close_socket(new_socket, client_address)
                        break
                elif (headPack[0] == 1):
                    datatemp = clients_name_ip[client_address] + " " +time.strftime("%X") + "\n" + body
                    for c in clients:
                        c.send(self.packdata(1, datatemp))
                    self.memberlist.insert('end', clients_name_ip[client_address] + " " +
                                           time.strftime("%X") + "\n" + body  )
                elif (headPack[0] == 3):
                    if(body=='online!'):
                        self.clients_ip_online[client_address] -= 1  # 在线
                    elif(body=='online?'):
                        self.memberlist.insert('end','online?\n')
                        new_socket.send(self.packdata(3, 'online!'))
                # 将此信息pop出去
                databuffer = databuffer[HEADERSIZE + bodysize:]

    # 文件传输粘包也是可以的，且每次传输定长的消息
    def recv_file(self,new_socket, name, client_address):
        self.clients_ip_tcp[client_address] = 1
        fileinfo_size = struct.calcsize('128sI')  # 返回格式字符串fmt描述的结构的字节大小
        try:
            # 获取打包好的文件信息， 并解包
            fhead = new_socket.recv(fileinfo_size)
            if(fhead=='agreement_upload_cancel'):
                return
            filename, filesize = struct.unpack('128sI', fhead)
            filename = filename.decode().strip('\00')
            # 文件名去掉\00，否则会报错
            with open(filename, 'wb') as f:
                ressize = filesize
                while True:
                    if ressize >1024:
                        filedata = new_socket.recv(1024)
                    else:
                        filedata = new_socket.recv(ressize)
                        f.write(filedata)
                        break
                    if not filedata:
                        break
                    f.write(filedata)
                    ressize = ressize - len(filedata)
                    if ressize < 0:
                        break
            datatemp = 'svr:' + self.clients_name_ip[client_address] + " " + time.strftime("%x") + "上传了文件： "+filename + "\n"
            for c in self.clients:
                c.send(self.packdata(0, datatemp))
            self.memberlist.insert('end', name + '上传了新的文件：' + filename + '\n')
        except Exception as e:
            new_socket.send(self.packdata(0, '文件上传失败\n'))
        self.clients_ip_tcp[client_address] = 0

    def return_file_list(self, new_socket, name, client_address):
        self.clients_ip_tcp[client_address] = 1
        # 发一个废包
        new_socket.send(self.packdata(10, 'pass'))
        # 获取文件目录
        files = os.listdir()
        # 用于传输文件目录的字符串
        liststr = ''
        # 将所有文件名传入字符串中
        for i in files:
            liststr += i + '\n'
        new_socket.send(liststr.encode())
        self.clients_ip_tcp[client_address] = 0

    # 向指定的客户发文件
    def send_file(self, new_socket, name, client_address):
        self.clients_ip_tcp[client_address] = 1
        # 发一个废包
        new_socket.send(self.packdata(10, 'pass'))
        # 获取文件目录
        files = os.listdir()
        while True:
            # 向客户端传送要下载的文件名，如果不存在就继续输入
            filename = new_socket.recv(100).decode()
            print(filename)
            if filename in files:
                new_socket.send('File_exists'.encode())
                # 将文件信息打包发送给客服端
                fhead = struct.pack('128sI', filename.encode(), os.stat(filename).st_size)
                new_socket.send(fhead)
                # 传送文件信息
                with open(filename, 'rb') as f:
                    while True:
                        filedata = f.read(1024)
                        if not filedata:
                            break
                        new_socket.send(filedata)
                self.memberlist.insert('end', name + '下载了文件：' + filename)
                break
            else:
                new_socket.send('File_no_exists'.encode())
                break
        self.clients_ip_tcp[client_address] = 0

    # 对发送内容进行分类和打包
    def packdata(self, type, data):
        bodylen = len(data.encode())
        header = [type, bodylen]
        headPack = struct.pack('!2I', *header)
        # !代表网络字节顺序NBO（Network Byte Order）,，2I代表2个unsigned int数据
        return headPack + data.encode()
    # 目前定义的消息类型有 0：服务端消息 1：聊天消息广播 10：废包

    # 关闭资源
    def close_socket(self, new_socket, client_address):
        try:
            self.clients.remove(new_socket)
        except:
            pass
        new_socket.close()
        self.memberlist.insert('end',self.clients_name_ip[client_address] + "已经离开\n")
        # 通知所有客户端，该客户已经离开
        datatemp = self.clients_name_ip[client_address] + "已经离开了"
        for c in self.clients:
            c.send(self.packdata(0, datatemp))

if __name__ == '__main__':
    server0 = Server()
