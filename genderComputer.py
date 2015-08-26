# vim: noet ts=4 sts=4 sw=4:
# This Python file uses the following encoding: utf-8

"""Copyright 2012-2013
Eindhoven University of Technology
Bogdan Vasilescu

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""

import os
import re
from dictUtils import MyDict
from unicodeMagic import UnicodeReader
from unidecode import unidecode
from nameUtils import only_greek_chars, only_cyrillic_chars
from nameUtils import leet2eng, inverseNameParts, extractFirstName
from filters import normaliseCountryName

'''Load the male and female name lists for <country>'''
def loadData(country, dataPath, hasHeader=True):
	def loadGenderList(gender, country, dataPath, hasHeader):
		fd = open(os.path.join(dataPath, '%s%sUTF8.csv' % (country, gender)), 'rb')
		reader = UnicodeReader(fd)
		names = {}
		if hasHeader:
			unused_header = reader.next()
		'''Load names as-is, but lower cased'''
		for row in reader:
			name = row[0].lower()
			try:
				'''The second column should be the count
				(number of babies in some year with this name)'''
				count = row[1]
			except:
				'''If second column does not exist, default to count=1'''
				count = 1
				if names.has_key(name):
					'''If here then I've seen this name before, modulo case.
					Only count once (there is no frequency information anyway)'''
					count = 0
			if names.has_key(name):
				names[name] += count
			else:
				names[name] = count
		fd.close()
		
		'''Add versions without diacritics'''
		for name in names.keys():
			dname = unidecode(name)
			if not names.has_key(dname):
				names[dname] = names[name]

		return names

	males = loadGenderList('Male', country, dataPath, hasHeader)
	females = loadGenderList('Female', country, dataPath, hasHeader)	
	return males, females


class GenderComputer():
	def __init__(self, nameListsPath):
		'''Data path'''
		self.dataPath = os.path.abspath(nameListsPath)
		
		'''gender.c, already lowercase'''
		self.genderDict = MyDict(os.path.join(self.dataPath, 'gender.dict'))
		
		'''Order of countries (columns) in the 
		nam_dict.txt file shipped together with gender.c'''
		self.countriesOrder = {
			'UK':0,
			'Ireland':1,
			'USA':2,
			'Italy':3,
			'Malta':4,
			'Portugal':5,
			'Spain':6,
			'France':7,
			'Belgium':8,
			'Luxembourg':9,
			'The Netherlands':10,
			'East Frisia':11,
			'Germany':12,
			'Austria':13,
			'Switzerland':14,
			'Iceland':15,
			'Denmark':16,
			'Norway':17,
			'Sweden':18,
			'Finland':19,
			'Estonia':20,
			'Latvia':21,
			'Lithuania':22,
			'Poland':23,
			'Czech Republic':24,
			'Slovakia':25,
			'Hungary':26,
			'Romania':27,
			'Bulgaria':28,
			'Bosnia and Herzegovina':29,
			'Croatia':30,
			'Kosovo':31,
			'Macedonia (FYROM)':32,
			'Montenegro':33,
			'Serbia':34,
			'Slovenia':35,
			'Albania':36,
			'Greece':37,
			'Russia':38,
			'Belarus':39,
			'Moldova':40,
			'Ukraine':41,
			'Armenia':42,
			'Azerbaijan':43,
			'Georgia':44,
			'Kazakhstan':45,
			'Turkey':46,
			'Arabia/Persia':47,
			'Israel':48,
			'China':49,
			'India/Sri Lanka':50,
			'Japan':51,
			'Korea':52,
			'Vietnam':53,
			'other countries':54,
		}
		self.countriesOrderRev = {}
		for country, idx in self.countriesOrder.items():
			self.countriesOrderRev[idx] = country
		
		self.threshold = 0.5
		
		self.nameLists = {}
		
		'''Name lists per country'''
		listOfCountries = ['Afganistan', 'Albania', 'Australia', 'Belgium', 'Brazil', 
						'Canada', 'Czech', 'Finland', 'Greece', 'Hungary', 'India', 'Iran', 
						'Ireland', 'Israel', 'Italy', 'Latvia', 'Norway', 'Poland', 'Romania', 
						'Russia', 'Slovenia', 'Somalia', 'Spain', 'Sweden', 'Turkey', 'UK', 
						'Ukraine', 'USA']
		for country in listOfCountries:
			self.nameLists[country] = {}
			self.nameLists[country]['male'], self.nameLists[country]['female'] = loadData(country, self.dataPath, hasHeader=False)
		
		'''Exceptions (approximations)'''
		#malesFrance, femalesFrance = loadData('Wallonia', self.dataPath, False)
		#self.nameLists['France'] = {}
		#self.nameLists['France']['male'] 	= malesFrance
		#self.nameLists['France']['female'] 	= femalesFrance
		
		malesNL, femalesNL = loadData('Frisia', self.dataPath, False)
		self.nameLists['The Netherlands'] = {}
		self.nameLists['The Netherlands']['male'] 	= malesNL
		self.nameLists['The Netherlands']['female'] = femalesNL
		
		'''Diminutives list'''
		fd = open(os.path.join(self.dataPath, 'diminutives.csv'), 'rb')
		reader = UnicodeReader(fd)
		self.diminutives = {}
		for row in reader:
			mainName = row[0].strip().lower()
			for diminutive in row[1:]:
				try:
					self.diminutives[diminutive].add(mainName)
				except:
					self.diminutives[diminutive] = set()
					self.diminutives[diminutive].add(mainName)
					
		'''Distribution of StackOverflow users per different countries'''			
		fd = open(os.path.join(self.dataPath, 'countryStats.csv'), 'rb')
		reader = UnicodeReader(fd)
		self.countryStats = {}
		total = 0.0
		for row in reader:
			country = row[0]
			numUsers = float(row[1])
			total += numUsers
			self.countryStats[country] = numUsers
		for country in self.countryStats.keys():
			self.countryStats[country] = self.countryStats[country] / total
		
		print 'Finished initialization'
	
	
	'''Look <firstName> (and potentially its diminutives) up for <country>.
	Decide gender based on frequency.'''
	def frequencyBasedLookup(self, firstName, country, withDiminutives=False):
		dims = set([firstName])
		if withDiminutives:
			try:
				dims = self.diminutives[firstName] # Includes firstName
				dims.add(firstName)
			except:
				pass
		
		countMale = 0.0
		countFemale = 0.0
		for name in dims:
			try:
				countMale += float(self.nameLists[country]['male'][name])
			except:
				pass
			try:
				countFemale += float(self.nameLists[country]['female'][name])
			except:
				pass
		
		if countMale > 0:
			if countFemale > 0:
				if countMale != 1.0 or countFemale != 1.0:
					if countMale > countFemale:
						prob = countFemale / countMale
						if prob < self.threshold:
							gender = "mostly male"
						else:
							gender = "unisex"
					else:
						prob = countMale / countFemale
						if prob < self.threshold:
							gender = "mostly female"
						else:
							gender = "unisex"
				else:
					gender = "unisex"
			else:
				gender = "male"
		else:
			if countFemale > 0:
				gender = "female"
			else:
				gender = None
		
		return gender
	
	
	'''Wrapper for <frequencyBasedLookup> that checks if data for the query <country>
	exists; can format the output.'''
	def countryLookup(self, firstName, country, withDiminutives):
		if country in self.nameLists.keys():
			return self.frequencyBasedLookup(firstName, country, withDiminutives)
		return None
	
	
	'''Search for a given <firstName> in the gender.c database.
	strict=True 	: look only in <country>'''
	def genderDotCLookup(self, firstName, country, strict=True):
		gender = None
		genderCountry = None
		country = normaliseCountryName(country)
		
		try: 
			'''Name in dictionary'''
			nameData = self.genderDict[firstName.lower()]
			
			def lab2key(lab):
				if lab in ['M', '1M', '?M']:
					return 'mmale'
				elif lab in ['F', '1F', '?F']:
					return 'mfemale'
				elif lab == '?':
					return 'uni'
			
			d = {}
			for lab in ['M', '1M', '?M', 'F', '1F', '?F', '?']:
				d[lab2key(lab)] = 0.0
			
			for [mf, frequencies] in nameData:
				for idx in range(len(frequencies)):
					hexFreq = frequencies[idx]
					if len(hexFreq.strip()) == 1:
						d[lab2key(mf)] += int(hexFreq, 16)
			
			thr = 256
			if d['mmale'] - d['mfemale'] > thr:
				gender = 'male'
			elif (thr >= d['mmale']-d['mfemale']) and (d['mmale'] > d['mfemale']):
				gender = 'mostly male'
			elif d['mfemale'] - d['mmale'] > thr:
				gender = 'female'
			elif (thr >= d['mfemale']-d['mmale']) and (d['mfemale'] > d['mmale']):
				gender = 'mostly female'
			else:
				gender = 'unisex'
			
			'''Options:
			1. I query for an existing name in a known country
			2. I query for an existing name in a country other
			than the ones I have data for'''
			if country in self.countriesOrder.keys():
				'''Here I still don't know if I have frequency information
				for this name and this country'''
				countryData = []
				'''[mf, frequencies] mf = M,1M,?M, F,1F,?F, ?, ='''
				for [mf, frequencies] in nameData:
					f = frequencies[self.countriesOrder[country]]
					if len(f.strip()) == 1:
						'''The name exists for that country'''
						countryData.append([mf, int(f, 16)])
				
				if len(countryData) == 1:
					'''The name is known for this country, and so is its gender'''
					genderCode = countryData[0][0]
					if genderCode == 'M':
						genderCountry = "male"
					elif genderCode in ['1M', '?M']:
						genderCountry = "mostly male"
					elif genderCode == 'F':
						genderCountry = "female"
					elif genderCode in ['1F', '?F']:
						genderCountry = "mostly female"
					elif genderCode == '?':
						genderCountry = "unisex"
		except:
			gender = None
		
		if strict:
			gender = genderCountry

		return gender
	
	
	
	''''Try to resolve gender based on <firstName>.
	Look in all countries and resort to arbitrage.'''
	def resolveFirstNameOverall(self, firstName, withDiminutives):
		'''Try each available country list in turn,
		and record frequency information.'''
		genders = set()
		arbiter = {}
		for country in self.nameLists.keys():
			gender = self.countryLookup(firstName, country, withDiminutives)
			if gender is not None:
				genders.add(gender)
				try:
					arbiter[gender] += self.countryStats[country]
				except:
					arbiter[gender] = self.countryStats[country]
		
		'''Keep the gender with the highest total count
		(frequency) aggregated across all countries.'''
		l = [(g,c) for g, c in arbiter.items()]
		if len(l):
			ml = max(l, key=lambda pair:pair[1])
			gender = ml[0]
			return gender
					
		# If all countries agree on gender, keep. Otherwise ignore
#		if len(genders) == 1:
#			return list(genders)[0]
		
		'''I might have the name in gender.c, but for a different country'''
		gender = self.genderDotCLookup(firstName, country, strict=False)
		return gender
	
	
	
	'''Main gender resolution function. Process:
	- if name is written in Cyrillic or Greek, transliterate
	- if country in {Russia, Belarus, ...}, check suffix
		* name might be inversed, so also try inverse if direct fails
	- extract first name and try to resolve
		* name might be inversed, so also try inverse if direct fails
	- assume name is in fact username, and try different tricks:
		* if country in {The Netherlands, ..}, look for vd, van, ..
		* try to guess name from vbogdan and bogdanv
	- if still nothing, inverse and try first name again (maybe country was empty)'''
	def resolveGender(self, name, country):

		# Check if name is written in Cyrillic or Greek script, and transliterate
		if only_cyrillic_chars(name) or only_greek_chars(name):
			name = unidecode(name)
		
		firstName = extractFirstName(name, 'direct')
		
		gender = self.tryCrossCountry(firstName)
		if gender is not None:
			return gender

		gender = self.tryUnidecoded(name)
		if gender is not None:
			return gender
		
		gender = self.tryRemovingFirstAndLastLetters(name)
		if gender is not None:
			return gender

		return None

	def tryCrossCountry(self, firstName):
		return self.resolveFirstNameOverall(firstName, True)

	def tryUnidecoded(self, name):
		dname = unidecode(name)
		firstName = extractFirstName(dname, 'direct')
		return self.tryCrossCountry(firstName)

	def tryRemovingFirstAndLastLetters(self, name):
		if len(name.split()) == 1:
			firstName = name[:-1].lower()
			gender = self.tryCrossCountry(firstName)
			if gender is not None:
				return gender

			firstName = name[1:].lower()
			gender = self.tryCrossCountry(firstName)
			return gender
		return None
	


if __name__=="__main__":
	import os
	from testSuites import testSuite1, testSuite2
	
	dataPath = os.path.abspath(".")
	gc = GenderComputer(os.path.join(dataPath, 'nameLists'))
	
	print 'Test suite 1'
	for (name, country) in testSuite1:
		print [unidecode(name), country], gc.resolveGender(name, country)
	
	print
	print 'Test suite 2'
	for (name, country) in testSuite2:
		print [unidecode(name), country], gc.resolveGender(name, country)
