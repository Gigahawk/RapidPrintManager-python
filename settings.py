from configparser import *

class settings(object):

	def __init__(self):
		self.config = ConfigParser()
		with open('settings.ini','r') as fp:
			self.config.readfp(fp)
		print(self.config.sections())

	def setVal(self,section,key,value, flush=True):
		self.config[section][key] = str(value)
		if flush:
			self.flush() 

	def setStrList(self,section,key,array, flush=True):
		out = ""
		for item in array:
			out += str(item) + ','
		out = out[:-1]
		self.config[section][key] = out
		if flush:
			self.flush()

	def getInt(self,section,key):
		return int(self.config[section][key])

	def getFloat(self,section,key):
		return float(self.config[section][key])

	def getBool(self,section,key):
		return self.config[section][key].lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']

	def getString(self,section,key):
		return self.config[section][key]

	def getStrList(self, section,key):
		listStr = self.config[section][key]
		if listStr:
			return listStr.split(',')
		else:
			return []

	def flush(self):
		with open('settings.ini','r+') as fp:
			self.config.write(fp)

