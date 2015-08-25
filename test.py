import os
from genderComputer import GenderComputer
gc = GenderComputer(os.path.abspath('./nameLists'))

print gc.resolveGender(unicode('Alexei Matrosov'), unicode('Russia'))
