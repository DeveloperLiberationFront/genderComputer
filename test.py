import os
import sys
from genderComputer import GenderComputer
gc = GenderComputer(os.path.abspath('./nameLists'))

for name in sys.argv[1:]:
    name = unicode(name)
    print name, gc.resolveGender(name, None)
