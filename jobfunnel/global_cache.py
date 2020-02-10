from collections import defaultdict as dd 
import os.path

glob_cache = dd(dd)

def get_prev_cache():
    if os.path.isfile('global_hash.txt'):
        file = open('global_hash.txt','r')
        temp = file.read()
        content = []
        curr= ''
        for i in range(len(temp)):
            if(temp[i]!=' '):
                curr+=temp[i]
            else:
                content.append(curr)
                curr = ''
        print('content',content)
        for i in range(0,len(content),3):
            key,country,ts = content[i],content[i+1],content[i+2]
            print('key',key,'country',country,'ts',ts)
            glob_cache[key][country] = ts
        file.close()
    print('glob',glob_cache)









