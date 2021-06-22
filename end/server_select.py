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
import select

# 定义工作线程数量
workerthreadnum = 4
inputs = {}  # 有消息到来的socket
outputs = {}  # databuffer中有数据待处理的socket
databuffer = {}  # 集合内部为键值对，socket和bytes变量匹配，作为各个用户的消息缓冲区
HEADERSIZE = 8   # 预定的头文件的大小
client_ip_status = {}  # 当用户此时在发送文件时置为1暂时不做心跳包
client_ip_file = {}  # 用户传输文件时的文件指针
client_ip_filesize = {}  # 用户传输文件的文件大小

class Server(object):
    # 初始化
    def __init__(self):
        # 创建工作线程
        for i in range(0, workerthreadnum):
            inputs[i] = []
            outputs[i] = []
            woker = Thread(target=self.workerThread, args=(i,))
            woker.start()
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
        # 自动获取ip
        hostname = socket.gethostname()
        iplt = socket.gethostbyname_ex(hostname)
        self.serverip = iplt[2][2]
        # port
        self.serverport = 1235
        # 服务器控制界面
        self.ui()

    # 后天界面
    def ui(self):
        self.window = tk.Tk()
        self.window.title("服务端后台")
        self.window.geometry('500x530+700+200')
        # ip展示
        tk.Label(self.window, text='IP: '+self.serverip).place(x=50, y=30)
        # 端口号展示
        tk.Label(self.window, text='port: '+str(self.serverport)).place(x=50,y=60)
        # 聊天室后台,memberllist就是输入框代号
        self.memberlist = tk.Text(self.window, width=55, height=20)
        self.memberlist.place(x=50, y=100)
        # 开始按钮
        stbtn = tk.Button(self.window, text='start', command=self.start).place(x=50, y=400)
        # 关闭按钮
        qtbtn = tk.Button(self.window,text='destroy', command=self.exitprogram).place(x=385, y=400)
        self.window.mainloop()

    # 初始化建立套接字线程和心跳包线程
    def start(self):
        # 建立欢迎套接字的进程
        Thread(target=self.svsocket).start()
        # 建立发送心跳包的线程
        # Thread(target=self.heart).start()

    # 创建欢迎套接字
    def svsocket(self):
        # 创建TCP欢迎套接字
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 本地ip和端口号
        self.local_addr = ('127.0.0.1', 1235)
        # self.local_addr = (self.serverip, 1235)
        # 绑定本地ip
        self.server_socket.bind(self.local_addr)
        self.server_socket.listen(1024)
        self.memberlist.insert('end', "服务器启动成功，等待客户连接......\n")
        self.get_conn()
        # 监听客户端与服务器连接

    # 退出程序
    def exitprogram(self):
        for c in self.clients:
            c.send(self.packdata(0, '服务器已经正常关闭'))
            c.close()
        os._exit(0)    # 在子进程中通过os._exit关闭整个进程
         # 服务端退出

    # 四个工作线程依次处理连入请求
    def get_conn(self):
        index = 0
        while True:
            # 给客户端分配一个新的socket，获取客户端的ip地址
            new_socket, client_address = self.server_socket.accept()
            new_socket.setblocking(False)
            # 用户出生
            self.clients_ip_online[new_socket] = 0
            client_ip_status[new_socket] = 0
            # 连接的所有用户添加到服务器的用户列表里面
            self.clients.append(new_socket)
            inputs[index%workerthreadnum].append(new_socket)
            databuffer[new_socket] = bytes()
            index = index + 1

    # 单个工作线程处理用户消息
    def workerThread(self,workerID):
        # 当前监听的inputs和outputs均为空,原地等待
        while(len(inputs[workerID]) + len(outputs[workerID]))<=0:
            time.sleep(0.5)
        while True:
            r_list, w_list, e_list = select.select(inputs[workerID], outputs[workerID],inputs[workerID],100)
            for obj in r_list:  # 这里的obj就是有消息到来的soket
                try:
                    data = obj.recv(1024)
                except:
                    self.close_socket(obj)
                    continue
                if data:
                    # 将数据库存入缓冲区，类似于push数据
                    databuffer[obj] += data
                # 将该连接存到outputs里面等待select
                if obj not in outputs[workerID]:
                    outputs[workerID].append(obj)
            for obj in w_list:  # wlist中为有消息待处理的socket
                while len(databuffer[obj]) > HEADERSIZE:
                    headPack = struct.unpack('!2I', databuffer[obj][:HEADERSIZE])
                    bodysize = headPack[1]
                    if len(databuffer[obj]) < HEADERSIZE+bodysize:
                        break
                    if(headPack[0]==5 or headPack[0]==6): #文件传输中特殊的消息体类型--字节流
                        body = databuffer[obj][HEADERSIZE:HEADERSIZE+bodysize]
                    else:
                        body = databuffer[obj][HEADERSIZE:HEADERSIZE + bodysize].decode()
                    self.dealdata(obj, headPack, body)
                    # 获取下一个数据包， 类似于把数据pop出去
                    databuffer[obj] = databuffer[obj][HEADERSIZE+bodysize:]
                # 处理完以后不再接听该socket，直到该socket再次发数据
                outputs[workerID].remove(obj)

    # 用户消息分类处理
    def dealdata(self, obj, headPack, body):
        # obj是对象的套接字，headPack是消息头，body是已经解压好的内容
        if (headPack[0] == 2): # 2是名字流类型
            # 将昵称和ip进行绑定
            self.clients_name_ip[obj] = body
            # 广播新用户加入的消息
            datatemp = self.clients_name_ip[obj] + " " + time.strftime("%x") + "加入聊天室" + "\n"
            for c in self.clients:
                c.send(self.packdata(0, datatemp))
            self.memberlist.insert('end', '  ' + self.clients_name_ip[obj] + " " + time.strftime(
                    "%x") + "加入聊天室" + '\n')
        elif (headPack[0] == 0): # 0是客户端和用户的系统消息
            if(body == 'agreement_quit'):
                self.close_socket(obj)
            elif(body == 'agreement_file_list'):
                self.return_file_list(obj)
        elif (headPack[0]==1): # 1是普通的聊天消息
            datatemp=self.clients_name_ip[obj] + " " +time.strftime("%X") + "\n" + body
            for c in self.clients:
                if(c!=obj):
                    c.send(self.packdata(1, datatemp))
        elif (headPack[0]==3): # 3是心跳包消息
            if(body=='online!'):
                self.clients_ip_online[obj] -= 1
            elif (body == 'online?'):
                obj.send(self.packdata(3, 'online!'))
        elif (headPack[0]==5): # 5是上传文件和文件头消息
            fhead = body
            filename, filesize = struct.unpack('128sI', fhead)
            filename = filename.decode().strip('\00')
            # 文件名去掉\00，否则会报错
            client_ip_file[obj] = open(filename, 'wb')
            client_ip_filesize[obj] = filesize
            client_ip_status[obj] = 1
        elif (headPack[0]==6):   #6是文件流
            client_ip_file[obj].write(body)
            client_ip_filesize[obj] = client_ip_filesize[obj] - headPack[1]
            if(client_ip_filesize[obj]<=0):
                self.memberlist.insert('end', '新文件上传成功\n')
                client_ip_file[obj].close()
                client_ip_filesize[obj]=0
                client_ip_status[obj] = 0
                for c in self.clients:
                    c.send(self.packdata(0,self.clients_name_ip[obj]+' 上传新文件'))
        elif (headPack[0]==7):   #7是下载文件和文件名消息
            filename = body
            self.send_file(obj, filename)
        else:
            pass

    # 向指定的客户发文件
    def send_file(self, obj, filename):
        client_ip_status[obj] = 1
        # 获取文件目录
        files = os.listdir()
        if filename in files: # 检测文件是否存在
            # 将文件信息打包发送给客服端
            fhead = struct.pack('128sI', filename.encode(), os.stat(filename).st_size)
            obj.send(self.packbytes(5, fhead))
            # 传送文件信息
            with open(filename, 'rb') as f:
                while True:
                    filedata = f.read(1024)
                    if not filedata:
                        break
                    obj.send(self.packbytes(6, filedata))
            self.memberlist.insert('end', self.clients_name_ip[obj]+' :下载了文件'
                                   + filename + '\n')
        else:
            obj.send(self.packdata(0, '不存在此文件'))
        client_ip_status[obj] = 0

    # 将字符串消息进行加装消息头和打包处理
    def packdata(self, type, data):
        bodylen = len(data.encode())
        header = [type, bodylen]
        headPack = struct.pack('!2I', *header)
        # !代表网络字节顺序NBO（Network Byte Order）,，2I代表2个unsigned int数据
        return headPack + data.encode()

    # 将字节流消息进行加装消息头和打包处理
    def packbytes(self, type, stream):
        bodylen = len(stream)
        header = [type, bodylen]
        headPack = struct.pack('!2I', *header)
        return  headPack + stream

    # 关闭资源
    def close_socket(self, obj):
        try:
            self.clients.remove(obj)
        except:
            pass
        obj.close()
        self.memberlist.insert('end',self.clients_name_ip[obj] + "已经离开\n")
        # 通知所有客户端，该客户已经离开
        datatemp = self.clients_name_ip[obj] + "已经离开了"
        for c in self.clients:
            c.send(self.packdata(0, datatemp))

    # 返回文件列表
    def return_file_list(self, obj):
        # 获取文件目录
        files = os.listdir()
        # 用于传输文件目录的字符串
        liststr = ''
        # 将所有文件名传入字符串中
        for i in files:
            liststr += i + '\n'
        if(liststr==''):
            obj.send(self.packdata(2, '群文件为空'))
        else:
            obj.send(self.packdata(2, liststr))
'''
    def heart(self):
        while True:
            for c in self.clients:
                if client_ip_status[c] == 1:  # 此时正在传输文件，暂时不进行心跳检测
                    continue
                try:
                    c.send(self.packdata(3, 'online?'))
                except:
                    self.close_socket(c)
                    break
                self.clients_ip_online[c] += 1
                if self.clients_ip_online[c] > 20:
                    self.close_socket(c)
                    break
                time.sleep(2)
'''
if __name__ == '__main__':
    server0 = Server()
