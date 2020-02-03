from database import *
from collections import defaultdict as dd 

ctry_hash = dd(int)

for ctry in country_monster.keys():
    ctry_hash[ctry]+=1