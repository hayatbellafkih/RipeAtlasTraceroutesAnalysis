from athenaTools import *

import time
start = time.time()
import datetime


a,b,c=getRttDataAthena()

finalResult =[]
for k, v in a.iteritems():
    result=rttEvolution([a[k],c[k]],k,"")
    finalResult.append(result)

now = datetime.datetime.now()
filePath= str(now.strftime("%Y-%m-%d_%H-%M"))
fp = open('%s.json'%filePath, 'w')
for result in finalResult:
    json.dump(result, fp, default=str)

end = time.time()
print("TOTAL Time is "+ str(end - start))
