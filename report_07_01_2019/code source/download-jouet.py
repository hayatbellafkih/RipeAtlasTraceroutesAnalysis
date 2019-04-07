import sys
import os 
from datetime import datetime
from datetime import timedelta
from datetime import date
from dateutil import relativedelta
from ripe.atlas.cousteau import AtlasResultsRequest 
import json

import gzip


currDate = datetime(int(2018), int(01), int(01), 1,0,0)
lastDate = datetime(int(2018), int(01), int(01), 1,0,3)
kwargs = {
    "msm_id": 5004,
    "start": currDate,
    "stop": lastDate,
    # "probe_ids": [1,2,3,4]
}

is_success, results = AtlasResultsRequest(**kwargs).create()
#is_success =True
#results = []


if is_success :
        # results = list(results)
    # else:
        # Output file
        fi = gzip.open("jouet-%s-%s.json.gz"%(currDate, lastDate ) ,"wb")
        print("Storing data for  measurement id" )
        for en in results:
            json.dump(en, fi)
            fi.write("\n")
        fi.close()



