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

from emailSender import *

import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage



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

class warnings(object):
	def __init__(self, printOutput = False):
		self.output = ""
		self.printOutput = printOutput
		self.hasWarning = False
		self.hasError = False

	def warn(self, e):
		warning = "[Warning] %s\n" % (e)
		if self.printOutput:
			print(warning)
		self.output += warning
		self.hasWarning = True

	def error(self, e):
		error = "[Error] %s\n" % (e)
		if self.printOutput:
			print(error)
		self.output += error
		self.hasError = True

class stlFile(object):
	
	def __init__(self,fileName):
		self.name = fileName
		self.copies = 1

		print("Attempting to parse filename")
		try:
			nameArray = fileName.split('_')
			self.copies = int(nameArray[1])
		except:
			self.log.warn("Warning: Could not parse copies for %s", self.fileName)

class printJob(object):

	def __init__(self, driveService, sheetService, discountID, row):
		self.emailSender = sender()

		self.log = warnings(printOutput = True)

		self.driveService = driveService
		self.sheetService = sheetService
		self.discountID = discountID

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
		self.stlFiles = self.parseFileNames(str(row[12]))
		self.couponCode = str(row[13])
		# row[14] is how did you hear abt us

		self.sane = self.sanityCheck()

		self.platerConf = ""
		self.receipt = ""

		if not self.sane:
			# TODO: add email support
			print("Print job is not valid, skipping...")
			return

		self.process()

	def parseSupport(self, s_support):
		if s_support == "Yes":
			return True
		if s_support == "No":
			return False

		print("Warning Could not parse support string, returning false as fallback")
		return False

	def parseResolution(self, s_resolution):
		try:
			out = int(re.search('\d+',s_resolution).group())
		except:
			out = 200
			self.log.warn("Couldn't parse resolution string, assuming 200 microns")

		return float(out)/1000.0

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

		self.log.warn("Other material selected")
		return material.Other

	def parseInfill(self, s_infill):
		try:
			out = int(re.search('\d+',s_infill).group())
		except:
			out = 20
			self.log.warn("Couldn't parse infill, using 20% as fallback")

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

		self.log.warn("Couldn't parse color, using white as default")
		return color.White

	def parseFileNames(self, s_links):
		dlLinks = s_links.split(',')
		out = []
		for link in dlLinks:
			id = link.strip()[33:]
			fileName = self.driveService.files().get(fileId = id).execute().get('name')
			fileName = fileName.replace(' ','').lower()
			out.append(stlFile(fileName))

		print(out)
		return out

	def sanityCheck(self):
		sane = True

		# Check colors and materials match up
		if self.material == material.PLA:
			if self.color == color.Custom:
				self.log.error("PLA doesn't have custom colors")
				sane = False
		elif self.material == material.ABS:
			if not (self.color == color.White or self.color == color.Black):
				self.log.error("ABS is only available in black and white")
				sane = False
		else:
			if self.color != color.Custom:
				self.log.error("Specialty filaments are only available in one color")
				sane = False

		# Check resolution makes sense
		if self.resolution < 0.1 or self.resolution > 0.3:
			self.log.error("Cannot print at %.2f mm layer height" % self.resolution)
			sane = False

		# Check if infill makes sense
		if self.infill < 0 or self.infill > 100:
			self.log.error("Cannot print at %d%% infill" % self.infill)
			sane = False

		return sane

	def runCommand(self, cmdString, getOutput = False, shell = True):
		print("Running " + cmdString)
		cmdProcess = run(cmdString, stdout = PIPE if getOutput else None, stderr = STDOUT if getOutput else None, shell = shell)

		if getOutput:
			return cmdProcess.stdout.decode("utf-8")

	def process(self):
		for file in self.stlFiles:
			print("Tweaking " + file.name)
			self.rotate(file.name)
			sleep(1)
			if isfile("temp/tweaked_%s" % (file.name)):
				print("Adding tweaked_%s to platerConf" % (file.name))
				self.platerConf += ("tweaked_%s %d\n" % (file.name, file.copies))
			else:
				print("Couldn't find tweaked file, adding %s to platerConf instead" % (file.name))
				self.platerConf += ("%s %d\n" % (file.name, file.copies))

		numPlates = self.plate()
		plates = []

		# plater returns files starting at index 1
		for i in range(1,numPlates):
			plate = "plate_"+str(i).zfill(3)+".stl"
			print("Slicing " + plate)
			plates.append(self.slice(plate))

		self.calculateCost(plates)

		self.sendEmail()

	def rotate(self,fileName):
		if not isfile('temp/' + fileName):
			print("Tweaker cannot find file %s" % (fileName))
			return

		# Spawning another python process cause im too lazy to write a wrapper for this tbh
		cmdString = "python3 Tweaker-3/Tweaker.py -i temp/%s -x -o temp/tweaked_%s" % (fileName, fileName)
		
		self.runCommand(cmdString)

	def plate(self):
		with open('temp/plater.conf','w') as platerFile:
			platerFile.write(self.platerConf)

		cmdString = "plater -v -W 200 -H 200 temp/plater.conf"

		# SUPER INEFFICIENT BUT YOLO
		cmdOut = self.runCommand(cmdString, getOutput = True)
		cmdArray = cmdOut.splitlines()

		print(cmdOut)

		exportLines = 0
		for line in cmdArray:
			if "Exporting" in line:
				exportLines += 1

		print("Generated %d plates" % (exportLines-1))

		return exportLines

	def slice(self, fileName):
		if not isfile("temp/%s" % (fileName)):
			print("Slicer cannot find file %s" % (fileName))
			return

		# (infill_line_width)*100/(infill_sparse_density)*(2 if grid...)
		infill_line_distance = 0 if not self.infill else (0.4)*100/self.infill*2

		cmdString = ("CuraEngine slice -v "
			         "-j printDefinitions/prusa_i3_mk2.def.json "
			         "-s center_object=true "
			         "-s support_enable=true "
			         "-s layer_height=%.3f " 
			         "-s infill_line_distance=%f "
			         "-s wall_thickness=1.2 " 
			         "-s top_thickness=0.8 "
			         "-s bottom_thickness=0.8 "
			         "-o temp/%s.gcode "
			         "-l temp/%s") % (self.resolution, infill_line_distance, fileName, fileName)

		# SUPER INEFFICIENT BUT YOLO
		cmdOut = self.runCommand(cmdString, getOutput = True)
		cmdArray = cmdOut.splitlines() 

		# Get last 6 lines of output
		outArray = cmdArray[-6:-1]
		#outArray = outArray.append(cmdArray[-1]) #this is broken but its fine we dont need it anyways

		print("Print statistics:")
		for line in outArray:
			print(line)

		# length starts off in metres
		length = float(re.search('[+-]?([0-9]*[.])?[0-9]+',outArray[0]).group())
		length = length*1000

		print("Using %f mm of filament" % length)

		fil_price = length*self.material.value
		print("The print should cost $%.f" % (fil_price))

		# return an object with the data
		out = type('gcodeStats', (object,),{'fil_price': fil_price, 'raw': outArray})

		return out

	def parseDiscount(self, row,cost):
		conditions = str(row[2]).split(',')

		if '$' in str(row[1]):
			discount = int(re.search('\d+',str(row[1])).group())
		elif '%' in str(row[1]):
			percent = int(re.search('\d+',str(row[1])).group())
			discount = cost*percent/100

		print("Cost is " + str(cost))

		print("Discount should be " + str(discount))

		for condition in conditions:
			print("Checking condition " + condition)
			if 'cost' in condition:
				limit = int(re.search('\d+',condition).group())
				print("Found limit " + str(limit))
				if '<=' in condition:
					if cost <= limit:
						print("condition passed <=")
						continue
					else:
						print("condition failed <=")
						return 0
				if '>=' in condition:
					if cost >= limit:
						print("condition passed >=")
						continue
					else:
						print("condition failed >=")
						return 0
				if '>' in condition:
					if cost > limit:
						print("condition passed >")
						continue
					else:
						print("condition failed >")
						return 0
				if '<' in condition:
					if cost < limit:
						print("condition passed <")
						continue
					else:
						print("condition failed <")
						return 0

			if 'maxdiscount' in condition:
				maxdiscount = int(re.search('\d+',condition).group())
				print("Found maxdiscount " + str(maxdiscount))
				if maxdiscount < discount:
					print("Discont > maxdiscount, setting to max")
					discount = maxdiscount

		print("Final discount: " + str(discount))

		return discount


	def checkDiscount(self, cost):
		range = 'Sheet1!A2:D'
		sheetRequest = self.sheetService.spreadsheets().values().get(spreadsheetId = self.discountID, range = range).execute()
		values = sheetRequest.get('values', [])
		discount = 0

		for row in values:
			if self.couponCode.lower() == str(row[0]).lower():
				print("Matched couponCode to " + str(row[0]).lower() )
				discount = self.parseDiscount(row, cost)
				if discount:
					break

		return discount

	def calculateCost(self, plates):
		receipt = []

		numPlates = len(plates)

		receipt.append(("Setup Costs:", 5.00, numPlates))

		if self.color == color.Gold or self.color == color.Silver:
			colorCost = 1.00
		else:
			colorCost = 0

		receipt.append(("Color:", colorCost, numPlates))

		lh = self.resolution

		if (lh == 0.1 or (lh != 0.2 and lh != 0.3)):
			layerCost = 2.00
		else:
			layerCost = 0

		receipt.append(("Resolution:", layerCost, numPlates))


		for plate in plates:			
			index = plates.index(plate)
			cost = plate.fil_price
			receipt.append(("Plate %d:" % (index+1), cost, 1))

		receiptString = ""
		totalCost = 0
		for entry in receipt:
			if not entry[1]:
				continue

			cost = round(entry[1]*100)/100

			if not "Plate" in entry[0]:
				receiptString += "%s\t$%.2f x%d\n" % (entry[0], cost, entry[2])
				totalCost += entry[2]*cost
			else:
				receiptString += "%s\t$%.2f\n" % (entry[0], cost)
				totalCost += cost

		discount = self.checkDiscount(totalCost)

		discountedCost = totalCost - discount

		roundedCost = round(discountedCost*4)/4

		receiptString += "Total Cost: $%.2f\n" % (totalCost)

		if discount:
			receiptString += "Discount: $%.2f\n" % (float(discount))
			receiptString += "Discounted Cost: $%.2f\n" % (discountedCost)
		
		receiptString += "Rounded Cost: $%.2f\n" % (roundedCost)

		self.receipt = receiptString
		print(receiptString)

	def sendEmail(self):
		print("Generating email...")
		msg = "Hello %s, here is the quote for your print order:\n\n" % (self.name)
		msg += self.receipt

		if self.log.hasError:
			msg += "\n There were some problems with your order, please resubmit your order with valid options \n"
			msg += self.log.output
		elif self.log.hasWarning:
			msg += "\n There were some problems with your order which we have tried to correct. If you are not satisfied, please resubmit your order. \n"
			msg += self.log.output

		msg += "\n We will send you another email shortly to confirm payment times, if you would like to cancel your order, please say so smth smth lol\n"
		msg += "\n Thanks, RapidBot"

		print(msg)

		self.emailSender.sendMessage(msg, self.email)




















