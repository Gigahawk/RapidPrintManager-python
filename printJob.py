from enum import Enum
import re
from os.path import isfile
#from os import popen #apparently deprecated
from subprocess import run
from subprocess import Popen
from subprocess import PIPE
from subprocess import STDOUT
from math import pi
from time import sleep


area = pi*(1.75/2)**2 #mm2

# densities in g/mm3
d_pla = 0.00124 
d_abs = 0.00110
d_flex = 0.00125 # value from google, should do our own measurements in the future
d_t_pc = 0.00121 # value from google, should do our own measurements in the future
d_nylon = 0.00108 # value from google, for Taulman 645

# Values are prices/mm: area(mm^2)*density(g/mm^3)*price($/g)
class material(Enum):
	PLA = area*(d_pla)*(0.10)
	ABS = area*(d_abs)*(0.15)
	Flex = area*(d_flex)*(0.50)
	T_PolyCarb = area*(d_t_pc)*(0.50)
	Nylon = area*(d_nylon)*(0.50)
	Other = 99

class color(Enum):
	White = 0
	Black = 1
	D_Blue = 2
	Red = 3
	L_Green = 4
	Gold = 5
	Silver = 6
	Custom = 99 

class printJob(object):


	def __init__(self, driveService, row):
		self.driveService = driveService

		# row[0] is timestamp
		self.name = str(row[1])
		self.email = str(row[2])
		# row[3] is faculty
		# row[4] is phone number
		self.support = self.parseSupport(str(row[5]))
		# row[6] is support details
		self.resolution = self.parseResolution(str(row[7]))
		# row[8] is purpose
		self.material = self.parseMaterial(str(row[9]))
		self.infill = self.parseInfill(str(row[10]))
		self.color = self.parseColor(str(row[11]))
		self.fileNames = self.parseFileNames(str(row[12]))
		self.couponCode = str(row[13])
		# row[14] is how did you hear abt us
		
		self.sane = self.sanityCheck()

		self.platerConf = ""

		if not self.sane:
			print("Print job is not valid, skipping...")
			return

		# optimize positions before slicing
		self.process()

	def parseSupport(self, s_support):
		if s_support == "Yes":
			return True
		if s_support == "No":
			return False

		print("Warning: Could not parse support string, returning false as fallback")
		return False

	def parseResolution(self, s_resolution):
		try:
			out = int(re.search('\d+',s_resolution).group())
		except:
			out = 200
			print("Warning, couldn't parse resolution string, returning 200 microns as fallback")

		return out

	def parseMaterial(self, s_material):
		if s_material == "PLA ($0.10/gram, Standard strength and durability with Wide Range of Colors Avaliable, Corn Based and biodegradable)":
			return material.PLA
		if s_material == "ABS ($0.15/gram, Slightly Stronger and more heat resistant than PLA, Oil Based - Only in Black and White)":
			return material.ABS
		if s_material == "Ugly Flex ($0.50, Flexible and around 80% rubber elasticity - Red Color)":
			return material.Flex
		if s_material == "Tranparent PolyCarbonate ($0.50, Stronger Impact strength than ABS but difficult to Print) (Turns white-ish)":
			return material.T_PolyCarb
		if s_material == "Nylon ($0.50, Tough and Durable - Strongest and most difficult to Print)":
			return material.Nylon

		print("Warning: Other material selected")
		return material.Other

	def parseInfill(self, s_infill):
		try:
			out = int(re.search('\d+',s_infill).group())
		except:
			out = 20
			print("Warning, couldn't parse infill string, returning 20% as fallback")

		return out

	def parseColor(self, s_color):
		if s_color == "White (ABS + PLA)":
			return color.White
		if s_color == "Black (ABS + PLA)":
			return color.Black
		if s_color == "Dark Blue (PLA Only)":
			return color.D_Blue
		if s_color == "Red (PLA Only)":
			return color.Red
		if s_color == "Light Green (PLA Only)":
			return color.L_Green
		if s_color == "Gold (Extra $1) (PLA Only)":
			return color.Gold
		if s_color == "Silver (Extra $1) (PLA Only)":
			return color.Silver
		if s_color == "I picked a special filament that has one color":
			return color.Custom

		print("Warning: Couldn't parse color, setting to white by default")
		return color.White

	def parseFileNames(self, s_links):
		dlLinks = s_links.split(',')
		out = []
		for link in dlLinks:
			id = link.strip()[33:]
			fileName = self.driveService.files().get(fileId = id).execute().get('name')
			fileName = fileName.replace(' ','').lower()
			out.append(fileName)

		print(out)
		return out

	def sanityCheck(self):
		sane = True

		# Check colors and materials match up
		if self.material == material.PLA:
			if self.color == color.Custom:
				print("PLA doesn't have custom colors")
				sane = False
		elif self.material == material.ABS:
			if not (self.color == color.White or self.color == color.Black):
				print("ABS is only available in black and white")
				sane = False
		else:
			if self.color != color.Custom:
				print("Specialty filaments are only available in one color")
				sane = False

		# Check resolution makes sense
		if self.resolution < 100 or self.resolution > 300:
			print("Cannot print at " + str(self.resolution) + "microns")
			sane = False

		# Check if infill makes sense
		if self.infill < 0 or self.infill > 100:
			print("Cannot print at " + str(self.infill) + "% infill")
			sane = False

		return sane

	def rotate(self,fileName):
		if not isfile('temp/' + fileName):
			print("Tweaker cannot find file " + fileName)
			return

		# Spawning another python process cause im too lazy to write a wrapper for this tbh
		cmdText = "python3 Tweaker-3/Tweaker.py -i temp/" + fileName + " -x -o temp/tweaked_" + fileName
		print("Running " + cmdText)
		cmdProcess = run(cmdText, shell = True)

		# wait some time for file to update

	def plate(self):
		with open('temp/plater.conf','w') as platerFile:
			platerFile.write(self.platerConf)
		cmdText = "plater -W 200 -H 200 -s 5 temp/plater.conf"
		print("Running " + cmdText)
		cmdProcess = run(cmdText, shell = True)
		# cmdProcess = Popen(cmdText, stdin = PIPE, shell = True)
		# cmdProcess.communicate(input = self.platerConf.encode('utf-8'))
		# cmdProcess.stdin.close()
		# if cmdProcess.wait(100) != 0:
			# print("There were some errors")


	def process(self):
		for fileName in self.fileNames:
			print("Checking for valid numbered filename")
			copies = 1
			try:
				nameEntries = fileName.split('_')
				copies = int(nameEntries[1])
			except:
				print("Couldn't find number of copies to print, assuming 1")

			copies = str(copies)

			print("Tweaking " + fileName)
			self.rotate(fileName)
			sleep(1)
			if isfile('temp/tweaked_' + fileName):
				print("Adding tweaked_" + fileName + " to platerConf")
				self.platerConf += ("tweaked_"+fileName+" "+copies+"\n")
			else:
				print("Couldn't find tweaked file, adding " + fileName + " to platerConf")
				self.platerConf += (fileName+" "+copies+"\n")


			# tweaked = self.slice("tweaked_"+fileName)
			# orig = self.slice(fileName)



			# if tweaked:
			# 	if tweaked.fil_price > 0 and tweaked.fil_price < orig.fil_price:
			# 		print("Tweaked price is sane: " + str(tweaked.fil_price))
			# 		continue

			# print("Tweaked price is invalid, using default: " + str(orig.fil_price))
		self.plate()

	def slice(self, fileName):
		if not isfile('temp/' + fileName):
			print("Slicer cannot find file " + fileName)
			return

		cmdText = "CuraEngine slice -v -j printDefinitions/prusa_i3_mk2.def.json -s center_object=true -s support_enable=true -o temp/" + fileName + ".gcode -l temp/" + fileName
		print("Running" + cmdText)
		#cmdOut = popen(cmdText).read() # apparently deprecated
		cmdProcess = run(cmdText,stdout = PIPE, stderr = STDOUT, shell = True)
		cmdOut = cmdProcess.stdout.decode("utf-8")
		cmdArray = cmdOut.splitlines() # SUPER INEFFICIENT BUT YOLO

		# Get last 6 lines of output
		outArray = cmdArray[-6:-1]
		#outArray = outArray.append(cmdArray[-1]) #this is broken but its fine we dont need it anyways

		for line in outArray:
			print(line)

		# length starts off in metres
		length = float(re.search('[+-]?([0-9]*[.])?[0-9]+',outArray[0]).group())
		length = length*1000

		print("Using " + str(length) + "mm of filament")

		fil_price = length*self.material.value
		print("The print should cost " + str(fil_price))

		# return an object with the data
		out = type('gcodeStats', (object,),{'fil_price': fil_price, 'raw': outArray})

		return out




