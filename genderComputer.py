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
import subprocess
from dictUtils import MyDict
from unicodeMagic import UnicodeReader
from unidecode import unidecode
from nameUtils import only_greek_chars, only_cyrillic_chars
from nameUtils import leet2eng, inverseNameParts, extractFirstName
from filters import normaliseCountryName

class GenderComputer():
	def __init__(self, nameListsPath):
		os.chdir('0717-182')
		print os.getcwd()

	def resolveFirstNameOverall(self, firstName):
		args = ["./a.out", "-get_gender", firstName]
		output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
		output = re.search("'[^']+'$", output).group(0)
		output = output[1:len(output)-1]

		return output
	
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

		name = re.sub("\d+", "", name)

		gender = self.tryRemovingFirstAndLastLetters(name)
		if gender is not None:
			return gender

		return None

	def tryCrossCountry(self, firstName):
		return self.resolveFirstNameOverall(firstName)

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
