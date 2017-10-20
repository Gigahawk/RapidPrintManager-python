from enum import Enum
import re
from os.path import isfile
from os import popen

class material(Enum):
	PLA = 0
	ABS = 1
	Flex = 2
	T_PolyCarb = 3
	Nylon = 4
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


	def __init__(self, row):
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

		self.slice()

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
			out.append(link.strip()[33:]+'.stl')

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

		for fileName in self.fileNames:
			if not isfile('temp/' + fileName):
				print("Cannot find file " + fileName)
				sane = False

		return sane

	def slice(self):
		if not self.sane:
			print("Print job is not valid, skipping...")
			return

		for fileName in self.fileNames:
			cmdText = "CuraEngine slice -v -j printDefinitions/prusa_i3_mk2.def.json -o " + fileName + ".gcode -l temp/" + fileName
			print("Running " + cmdText)
			cmdOut = popen(cmdText).read()

			print(cmdOut)




