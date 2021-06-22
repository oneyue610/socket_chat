# encoding: utf-8
from PyQt5 import QtGui
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *
import tkinter as tk
import tkinter.messagebox
import sys, os
import socket
from threading import Thread
import  struct
import  operator
import time

# 通信双方需要知道包头的长度
HEADERSIZE = 8
# 我们需要一个缓存
dataBuffer = bytes()
# 获取包大小，并解压
FILEINFO_SIZE = struct.calcsize('128sI')

class Client(QWidget):
    def __init__(self):
        self.IP = '127.0.0.1'
        self.port = '1235'
        self.name = ''
        # 当该客户处于下载文件的状态时，讲接收信息进程置于忙等待
        self.tcplock = 0
        self.online = 0
        self.tcpstatus = 0
        self.welcome_gui()

    # 登录界面
    def welcome_gui(self):
        # 欢迎窗口
        self.window = tk.Tk()
        self.window.title('welcome')
        self.window.geometry('500x530+700+200')
        canvas = tk.Canvas(self.window, height=530, width=500)
        image_file = tk.PhotoImage(file='p0.gif')
        image = canvas.create_image(0, 0, anchor='nw', image=image_file)
        canvas.pack(side='top')
        # 输入IP
        tk.Label(self.window, text='IP').place(x=70, y=70)
        self.ipentry = tk.StringVar()
        self.ipentry.set('127.0.0.1')
        entry_ip = tk.Entry(self.window, textvariable=self.ipentry)
        entry_ip.place(x=120, y=70)
        # 输入port
        tk.Label(self.window, text='port').place(x=70, y=100)
        self.portentry = tk.IntVar()
        self.portentry.set(1235)
        entry_port = tk.Entry(self.window, textvariable=self.portentry)
        entry_port.place(x=120, y=100)
        # 输入name
        tk.Label(self.window, text='name').place(x=70, y=130)
        self.nameentry = tk.StringVar()
        self.nameentry.set('Li Hua')
        entry_name = tk.Entry(self.window, textvariable=self.nameentry)
        entry_name.place(x=120, y=130)
        # 连接按钮
        self.conbtn = tk.Button(self.window, text='login', command=self.connect)
        self.conbtn.place(x=400, y=450)
        self.window.mainloop()

    # 连入服务器
    def connect(self):
        self.IP = self.ipentry.get()
        self.port = self.portentry.get()
        self.name = self.nameentry.get()
        self.window.destroy()
        # 与服务器连接, 已经与服务器连接成功
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.local_addr = (self.IP, self.port)
        self.client_socket.connect(self.local_addr)
        # 发送名字
        self.client_socket.send(self.packdata(2, self.name))
        self.chat_gui()

    # 聊天界面
    def chat_gui(self):
        # 初始化一个主窗口
        QWidget.__init__(self)
        # 设置窗口的大小和位置，前二为窗口位置，后二宽高
        self.setGeometry(500, 200, 1000, 700)
        # 设置标题
        self.setWindowTitle("聊天室")
        # 添加背景
        palette = QtGui.QPalette()
        bg = QtGui.QPixmap(r"p2.png")
        palette.setBrush(self.backgroundRole(), QtGui.QBrush(bg))
        self.setPalette(palette)
        # 多行文本显示，显示所有的聊天信息
        self.content = QTextBrowser(self)
        self.content.setGeometry(50, 50, 900, 400)

        # 单行文本，消息发送框
        self.message = QLineEdit(self)
        self.message.setGeometry(50, 500, 800, 40)
        self.message.setPlaceholderText("输入发送内容")

        # 单行文本，文件上传框
        self.uploadpath = QLineEdit(self)
        self.uploadpath.setGeometry(50, 550, 800, 40)
        self.uploadpath.setPlaceholderText("上传文件路径")

        # 单行文本，文件下载框
        self.downloadname = QLineEdit(self)
        self.downloadname.setGeometry(150, 600, 700, 40)
        self.downloadname.setPlaceholderText("选择下载文件")

        # 发送按钮
        self.button = QPushButton("发送", self) # 第二个参数是父窗口
        self.button.setFont(QFont("微软雅黑", 10, QFont.Bold))
        self.button.setGeometry(880, 500, 70, 40)

        # 上传文件按钮
        self.buttonup = QPushButton("上传", self)
        self.buttonup.setFont(QFont("微软雅黑", 10, QFont.Bold))
        self.buttonup.setGeometry(880, 550, 70, 40)

        # 文件列表按钮
        self.buttonlt = QPushButton("文件", self)
        self.buttonlt.setFont(QFont("微软雅黑", 10, QFont.Bold))
        self.buttonlt.setGeometry(50, 600, 70, 40)
        self.buttonlt.clicked.connect(self.filelist)

        # 下载文件按钮
        self.buttondn = QPushButton("下载", self)
        self.buttondn.setFont(QFont("微软雅黑", 10, QFont.Bold))
        self.buttondn.setGeometry(880, 600, 70, 40)

        # 退出按钮
        self.buttonqu = QPushButton("退出", self)
        self.buttonqu.setFont(QFont("微软雅黑", 10, QFont.Bold))
        self.buttonqu.setGeometry(880, 650, 70, 40)
        self.buttonqu.clicked.connect(self.quit)

        # 启动线程
        self.work_thread()

    # 发送消息
    def send_msg(self):
        msg = self.message.text()
        try:
            self.client_socket.send(self.packdata(1, msg))
        except:
            self.client_socket.close()
            self.destroy()
            sys.exit()  # 发送失败退出聊天室时直接退出程序
        self.content.append("<font color=\"#804000\">" + self.name + ' '+time.strftime("%X")+"</font>")
        self.content.append("<font color=\"#804000\">" + msg + '\n'+"</font>")
        self.content.append("<font color=\"#804000\">" + ' ' + "</font>")
        self.message.clear()

    # 上传文件
    def upload_file(self):
        self.tcpstatus = 1
        # 获取路径
        path = self.uploadpath.text()
        # 获取文件名
        ns = path.rfind('\\')
        filename = path[ns + 1:]
        # 如何路径正确开始传输
        if os.path.exists(path):
            # 发文件消息头
            fhead = struct.pack('128sI', filename.encode(), os.stat(path).st_size)
            # os.stat(path).st_size 获得指定路径文件的大小
            self.client_socket.send(self.packbytes(5, fhead))
            print(path + '  ' + filename)
            # 传送文件
            with open(path, 'rb') as f:
                while True:
                    filedata = f.read(1024)
                    if not filedata:
                        break
                    self.client_socket.send(self.packbytes(6,filedata))
        else:
            self.content.append("<font color=\"#FF0000\">" + '状态：路径错误，请输入文件的绝对路径哦\n' + "</font>")
            self.content.append(' ')
        self.tcpstatus = 0

    # 获取文件列表
    def filelist(self):
        self.client_socket.send(self.packdata(0, 'agreement_file_list'))

    # 下载文件
    def download_file(self):
        self.tcpstatus = 1
        # 从用户输入接收文件名，并发送给服务端
        filename = self.downloadname.text()
        if(filename == ''):
            return
        # 通知服务端
        self.client_socket.send(self.packdata(7, filename))
        self.tcpstatus = 0

    # 接收消息
    def recv_msg(self):
        databuffer = bytes()
        while True:
            while(self.tcplock):
                continue
            try:
                data = self.client_socket.recv(1024)
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
                if(headPack[0]==5 or headPack[0]==6):
                    body = databuffer[HEADERSIZE:HEADERSIZE + bodysize]
                else:
                    body = databuffer[HEADERSIZE:HEADERSIZE + bodysize].decode()
                # 数据处理
                if(headPack[0]==0): #0是系统消息
                    body = body + "\n"
                    self.content.append("<font color=\"#014507\">" + '服务端:\n' + body + "</font>")
                    self.content.append(' ')
                    if (body == '服务器已经正常关闭\n'):
                        self.tcpstatus=1
                elif(headPack[0]==1): #1是聊天消息
                    body = body + '\n'
                    self.content.append(body)
                elif(headPack[0]==2): # 2是文件列表消息
                    self.content.append("<font color=\"#014507\">" + '文件列表：' + "</font>")
                    self.content.append(body)
                elif(headPack[0]==3): #3是心跳包消息
                    if(body == 'online?'):
                        self.client_socket.send(self.packdata(3, 'online!'))
                    elif (body == 'online!'):
                        self.online -= 1
                elif(headPack[0]==5): #下载文件文件头
                    fhead = body
                    filename, filesize = struct.unpack('128sI', fhead)
                    filename = filename.decode().strip('\00')
                    # 文件名去掉\00，否则会报错
                    self.f = open(filename, 'wb')
                    self.fsize = filesize
                    self.tcpstatus = 1
                elif(headPack[0]==6): #下载文件流
                    self.f.write(body)
                    self.fsize = self.fsize - headPack[1]
                    if(self.fsize <=0 ):
                        self.content.append("<font color=\"#00FF00\">" + '文件下载成功 ' + "</font>")
                        self.f.close()
                        self.fsize = 0
                        self.tcpstatus = 0
                else:
                    pass
                # 将此信息pop出去
                databuffer = databuffer[HEADERSIZE + bodysize:]

    # 退出功能
    def quit(self):
        try:
            self.client_socket.send(self.packdata(0, 'agreement_quit'))
        except:
            pass
        self.client_socket.close()
        self.destroy()
        sys.exit()  # 退出聊天室时直接退出程序

    # 点击按钮发送消息
    def btn_send(self):
        self.button.clicked.connect(self.send_msg)

    # 点击上传按钮上传文件
    def btn_upload(self):
        self.buttonup.clicked.connect(self.upload_file)

    # 点击下载按钮下载文件
    def btn_download(self):
        self.buttondn.clicked.connect(self.download_file)

    # 线程处理
    def work_thread(self):
        Thread(target=self.btn_send).start()
        Thread(target=self.recv_msg).start()
        Thread(target=self.btn_upload).start()
        Thread(target=self.btn_download).start()
        Thread(target=self.send_heart).start()

    # 对字符串消息进行分类和打包
    def packdata(self, type, data):
        bodylen = len(data.encode())
        header = [type, bodylen]
        headPack = struct.pack('!2I', *header)
        # !代表网络字节顺序NBO（Network Byte Order）,，2I代表2个unsigned int数据
        return headPack + data.encode()

    # 对字节流消息进行分类和打包
    def packbytes(self, type, stream):
        bodylen = len(stream)
        header = [type, bodylen]
        headPack = struct.pack('!2I', *header)
        return headPack + stream

    # 心跳包函数
    def send_heart(self):
        while True:
            while(self.tcpstatus):
                continue
            try:
                self.client_socket.send(self.packdata(3, 'online?'))
            except:
                self.content.append("<font color=\"#FF0000\">" + '服务端异常退出\n'+ "</font>")
                self.content.append(" ")
                break
            self.online += 1
            if self.online > 10:
                self.content.append("<font color=\"#FF0000\">" + '服务端异常退出\n'+ "</font>")
                self.content.append(" ")
                break
            time.sleep(2)

if __name__ == '__main__':
    app = QApplication(sys.argv) # 初始，负责整个图形界面的底层管理功能
    win = Client()
    win.show()  # 执行了show窗口才会展现
    app.exec_()  # 进入qt的事件处理循环