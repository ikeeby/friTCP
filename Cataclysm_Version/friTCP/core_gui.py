# core_gui.py
import sys
from PyQt5.QtWidgets import QDialog, QApplication, QMainWindow, QTableWidgetItem, QHeaderView,QTableWidget, QMessageBox,QLineEdit,QAbstractItemView
from PyQt5.QtGui import QStandardItemModel,QStandardItem, QPixmap,QIcon, QRegExpValidator
from PyQt5 import uic
from PyQt5.QtCore import Qt, QRegExp, QThread, pyqtSignal, pyqtSlot
from core_func import *
import ast

Ui_MainWindow, QtBaseClass = uic.loadUiType("main_window.ui")
hook_alert_Ui_MainWindow, hook_alert_QtBaseClass = uic.loadUiType("hook_alert_window.ui")
			
class MyWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MyWindow, self).__init__(parent)
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		
		self.process_list_set()
			
		self.ui.pushButton_hook.clicked.connect(self.hook_btn_clicked)
		self.ui.pushButton_refresh.clicked.connect(self.process_list_set)
		
		self.ui.pushButton_go.clicked.connect(self.intercept_go_button)
		self.ui.pushButton_interceptToggle.toggled.connect(self.toggle_intercept_on)
		
		# 아래 4 줄은 헥스뷰와 스트링뷰를 연동하기 위한 것.
		self.ui.tableWidget_hexTable.cellChanged.connect(self.intercept_hexTable_changed)
		self.ui.tableWidget_hexTable.itemSelectionChanged.connect(self.hexTable_itemSelected)
		
		self.ui.tableWidget_stringTable.cellChanged.connect(self.intercept_strTable_changed)
		self.ui.tableWidget_stringTable.itemSelectionChanged.connect(self.strTable_itemSelected)
	
	def process_list_set(self):
		header = self.ui.tableWidget_procList.horizontalHeader()       
		header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.Stretch)
		
		process_list = get_process_list()
		
		self.ui.tableWidget_procList.setRowCount(len(process_list))
				
		c = 0
		for proc in process_list:
			self.ui.tableWidget_procList.setItem(c, 0, QTableWidgetItem(str(proc[0])))
			self.ui.tableWidget_procList.setItem(c, 1, QTableWidgetItem(proc[1]))
			c += 1
			
		self.ui.tableWidget_procList.cellClicked.connect(self.process_clicked)
		self.ui.tableWidget_procList.cellDoubleClicked.connect(self.hook_btn_clicked)
	
	def process_clicked(self,row, col):
		proc_pid = self.ui.tableWidget_procList.item(row, 0).text()
		proc_name = self.ui.tableWidget_procList.item(row, 1).text()
		
		
		self.ui.lineEdit_pid_input.setText(proc_pid)
		# 상태바에 선택한 프로세스 정보 보여주기
		message = "PID : {} / Process Name : {}".format(proc_pid,proc_name)
		self.ui.statusbar.showMessage(message)

	def hook_btn_clicked(self):
		user_input_pid = self.ui.lineEdit_pid_input.text()
		
		self.open_alert_window(user_input_pid)
	
		#hook_function(pid)
	
	def open_alert_window(self,pid):
		self.hook_pid = pid
		self.alert_window = QMainWindow()
		self.alert_ui = hook_alert_Ui_MainWindow()
		self.alert_ui.setupUi(self.alert_window)
		self.alert_window.setWindowFlags(Qt.FramelessWindowHint)
		self.alert_window.show()
		self.frida_agent = FridaAgent(self.hook_pid, self)
		self.make_connection(self.frida_agent)
		self.alert_ui.pushButton_gogo.clicked.connect(self.close_alertwindow)
		
	def close_alertwindow(self):
		self.alert_window.close()
		
		# 두번째 proxy 탭으로 이동
		self.ui.tabWidget_tab.setCurrentIndex(1)
	
	def make_connection(self, class_object):
		class_object.from_agent_data.connect(self.from_fridaJS)
	
	@pyqtSlot(str)	
	def from_fridaJS(self,data):
		#self.ui.textBrowser_hexData.setText(data)
		#self.ui.textBrowser_hexData.append(str(message))
			
		if(data.startswith("[PROXY]")):
			func_name, ip_info, port_info = parsing_info(data)
			
			# 히스토리에 기록
			self.history_addRow(data)
			
			# 인터셉트 모드일 경우
			if(self.frida_agent.intercept_on):
				self.frida_agent.current_isIntercept = True
				hex_data = parsing_hex(data)
				self.intercept_view(hex_data)
				self.ui.tabWidget_proxyTab.setCurrentIndex(0)
				# 클릭을 연결해두기. (go button)
			else:
				user_input = ""
				script = self.frida_agent.script_list[func_name]
				script.post({'type':'input','payload':user_input})
	
	def history_addRow(self,history_item):
		func_name, ip_info, port_info = parsing_info(history_item)
		hex_list = parsing_hex(history_item)
				
		numRows = self.ui.tableWidget_proxyHistory.rowCount()
		
		self.ui.tableWidget_proxyHistory.insertRow(numRows)
		
		self.ui.tableWidget_proxyHistory.setItem(numRows, 1, QTableWidgetItem(func_name))
		self.ui.tableWidget_proxyHistory.setItem(numRows, 2, QTableWidgetItem(ip_info))
		self.ui.tableWidget_proxyHistory.setItem(numRows, 3, QTableWidgetItem(port_info))
		self.ui.tableWidget_proxyHistory.setItem(numRows, 4, QTableWidgetItem(str(hex_list)))
		
		self.ui.tableWidget_proxyHistory.cellClicked.connect(self.history_detail)
		
		current_item = self.ui.tableWidget_proxyHistory.item(numRows, 0)
		self.ui.tableWidget_proxyHistory.scrollToItem(current_item, QAbstractItemView.PositionAtTop)
		self.ui.tableWidget_proxyHistory.selectRow(numRows)
		
	def history_detail(self,row, col):
		hex_list = ast.literal_eval(self.ui.tableWidget_proxyHistory.item(row, 4).text())
		
		hex_text =""
		str_text = ""
		for hex in hex_list:
			hex_text += hex + " "
			str_text += chr(int(hex,16)) + " "
		
		self.ui.textBrowser_hexData.setText(hex_text)
		self.ui.textBrowser_stringData.setText(str_text)
		
	#"[PROXY][FUNC_NAME]"+hook_function_name+" [IP]"+socket_address.ip+" [PORT]"+socket_address.port+" "+"[HEXDUMP]"+buf_length+" " + res
	
	def intercept_view(self,hex_data):
		need_row_num = int(len(hex_data) / 16)
				
		#self.ui.tableWidget_hexTable.clearContents()
		
		for row in range(need_row_num+1):
			# 거꾸로 입력하기.
			#row = need_row_num - row
			numRows = self.ui.tableWidget_hexTable.rowCount()
		
			self.ui.tableWidget_hexTable.insertRow(numRows)
			self.ui.tableWidget_stringTable.insertRow(numRows)
			
			if(row< need_row_num):
				# 16번 반복
				for i in range(16):
					self.ui.tableWidget_hexTable.setItem(row, i, QTableWidgetItem(hex_data[(16*row)+i]))
					self.ui.tableWidget_hexTable.item(numRows,i).setTextAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
					
					self.ui.tableWidget_stringTable.setItem(row, i, QTableWidgetItem(chr(int(hex_data[(16*row)+i],16))))
					self.ui.tableWidget_stringTable.item(numRows,i).setTextAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
					
			else:
				# total_length - (need_row_num * 16)
				for i in range((len(hex_data)-(need_row_num * 16))):
					self.ui.tableWidget_hexTable.setItem(row, i, QTableWidgetItem(hex_data[(16*row)+i]))
					self.ui.tableWidget_hexTable.item(numRows,i).setTextAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
					
					self.ui.tableWidget_stringTable.setItem(row, i, QTableWidgetItem(chr(int(hex_data[(16*row)+i],16))))
					self.ui.tableWidget_stringTable.item(numRows,i).setTextAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
	
	
	def hexTableToList(self):
		hexTable = self.ui.tableWidget_hexTable
		hexList = []
		
		numRows = hexTable.rowCount()
		
		for i in range(numRows):
			for j in range(16):
				hexDataItem = hexTable.item(i, j)
				if hexDataItem != None:
					hexList.append(hexDataItem.text())
					
		return hexList
		
	def intercept_go_button(self):
		
		#self.ui.textBrowser_hexData.setText(str(hexList))
		
		if(self.frida_agent.current_isIntercept):
			hexList = self.hexTableToList()
			self.frida_agent.send_spoofData(hexList)
			
			for i in reversed(range(self.ui.tableWidget_hexTable.rowCount())):
				self.ui.tableWidget_hexTable.removeRow(i)
				
			for i in reversed(range(self.ui.tableWidget_stringTable.rowCount())):
				self.ui.tableWidget_stringTable.removeRow(i)
		
		self.ui.tableWidget_hexTable.setRowCount(0)
		self.ui.tableWidget_stringTable.setRowCount(0)
		
	def toggle_intercept_on(self):
		self.frida_agent.intercept_on = self.ui.pushButton_interceptToggle.isChecked()
		
		if(self.frida_agent.intercept_on):
			self.ui.pushButton_interceptToggle.setText("Intercept ON")
		else:
			self.ui.pushButton_interceptToggle.setText("Intercept OFF")
			
	def intercept_hexTable_changed(self,row, col):
		changed_data = self.ui.tableWidget_hexTable.item(row, col).text()
		
		try:
			tmp = int(changed_data,16)
		except Exception:
			changed_data = "00"
			
		if(len(changed_data) != 2):
			changed_data = "00"
		
		if(self.ui.tableWidget_hexTable.item(row, col) != None):
			self.ui.tableWidget_hexTable.item(row, col).setText(changed_data)
		if(self.ui.tableWidget_stringTable.item(row, col) != None):
			self.ui.tableWidget_stringTable.item(row, col).setText(chr(int(changed_data,16)))
		
	def hexTable_itemSelected(self):
		for sel_item in self.ui.tableWidget_hexTable.selectedItems():
			row = sel_item.row()
			col = sel_item.column()
			
			self.ui.tableWidget_stringTable.setCurrentCell(row,col)

	def intercept_strTable_changed(self,row, col):
		changed_data = self.ui.tableWidget_stringTable.item(row, col).text()
			
		if(len(changed_data) != 1):
			changed_data = " "
			
		self.ui.tableWidget_hexTable.item(row, col).setText(hex(ord(changed_data))[2:])
		self.ui.tableWidget_stringTable.item(row, col).setText(changed_data)
		
	def strTable_itemSelected(self):
		for sel_item in self.ui.tableWidget_stringTable.selectedItems():
			row = sel_item.row()
			col = sel_item.column()
			
			self.ui.tableWidget_hexTable.setCurrentCell(row,col)