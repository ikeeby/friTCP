import socket
import os
import time

print(os.getpid())
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 12346))
count = 1
while(True):
	#print(len("Hello Server!1234567890123456789012345678901234567890")*50)
	msg = ("Hello Server!test").encode()
	sock.send(msg)
	data = sock.recv(65535)
	#count = count * 2
	print(os.getpid())
	print(data.decode())
	time.sleep(1)

sock.close()