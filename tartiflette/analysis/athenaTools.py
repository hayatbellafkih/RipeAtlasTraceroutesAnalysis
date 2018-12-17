#imports

import os
import json
from bson import json_util
from multiprocessing import Pool
import rttAnalysis 
import re
import pymongo
import pygeoip
import calendar
import time
from collections import defaultdict
import sys
import datetime
from datetime import timedelta
import numpy as np
import boto3
import ConfigParser, os


def load_sql_request_by_file(filename=''):

    request_file= open(filename, 'r')
    request= request_file.readline()
    return (request)

def generateSQLAthenaRequest (start, end,currentTimestamp, endTimestamp, msmIds=[]):

	#msmIds=[5,9,7] => 5 OR 9 OR 7
	print("msmIds   "+ str(msmIds))
	msm=""
	i= 0
	while i< len(msmIds) -1:
		print (msm)
		print("i            "+ str(i))
		msm=   " %s msm= '%s' OR "%(msm, msmIds[i])
		i=i+1
	msm = "%s msm = '%s' "%(msm, msmIds[i])
	
	print (msm)
	
		
	delta = end -start         # timedelta
	ors = list()
	for i in range(delta.days + 1):
		tmpDate = start + timedelta(i)
		partialPartSqlRequest= "(year = '%s' and month = '%s' and day = '%s' and (%s))"%(tmpDate.year, tmpDate.month, tmpDate.day, msm)
		ors.append(partialPartSqlRequest)

	total = len(ors)
	count =0
	s="("
	while( count < total -1):
		s= s + ors[count] + " OR "
		count =count + 1
		
	s= s+  ors[count] + ")"

	print ("Final request = "+s)
	
	sqlRequest= load_sql_request_by_file("sqlRequestForAthena.sql")
	finalRequest= sqlRequest.format( currentTimestamp, endTimestamp, s)
	
	print(finalRequest)
	
	return finalRequest


def getRttDiff(configFile=None):
    """
		Notes: takes about 6G of RAM for 1 week of data for 1 measurement id
    """
    #Find aws configuration
    config = ConfigParser.ConfigParser()
    config.readfp(open('AwsConfig.ini'))
    print(config)
    
    secret= config.get("default", "aws_access_key_id")
    access= config.get("default", "aws_secret_access_key")
    
    print("Find RTT differentiel for each traceroute")

    if configFile is None:
        configFile = "conf/getRttDataAthena.conf"

    if os.path.exists(configFile):
        expParam = json.load(open(configFile, "r"), object_hook=json_util.object_hook)


    else:
        sys.stderr("No config file found!\nPlease copy conf/%s.default to conf/%s\n" % (configFile, configFile))

    pool = Pool(expParam["nbProcesses"], initializer=rttAnalysis.processInit)  # , maxtasksperchild=binMult)

    if not expParam["prefixes"] is None:
        expParam["prefixes"] = re.compile(expParam["prefixes"])
    client = pymongo.MongoClient("mongodb-iijlab")
    db = client.atlas
    detectionExperiments = db.rttExperiments
    alarmsCollection = db.rttChanges
    # expId = detectionExperiments.insert_one(expParam).inserted_id

    sampleMediandiff = {}
    ip2asn = {}
    gi = pygeoip.GeoIP("../lib/GeoIPASNum.dat")

    start = int(calendar.timegm(expParam["start"].timetuple()))
    end = int(calendar.timegm(expParam["end"].timetuple()))

    rawDiffRtt = defaultdict(list)
    rawNbProbes = defaultdict(list)
    rawDates = defaultdict(list)

    # print(start,'#########"', expParam["start"])
    # print(end,'#########', expParam["end"])
    # print(range(start,end,expParam["timeWindow"]))
    # sys.exit(0)
    
    
    # AWS Athena connection
    client = boto3.client("athena",
	aws_access_key_id=access,
	aws_secret_access_key=secret	)
    for currDate in range(start, end, expParam["timeWindow"]):

        sys.stderr.write("Rtt analysis %s" % datetime.datetime.utcfromtimestamp(currDate))
        tsS = time.time()

        diffRtt = defaultdict(dict)
        nbRow = 0
        
        #SQL request parameters
	print(expParam)
        currDatetime= datetime.datetime.utcfromtimestamp(int(currDate))
        endDatetime= datetime.datetime.utcfromtimestamp(int(currDate+int(expParam["timeWindow"])))
	msmIds= expParam["msmIds"]
        msmType=  expParam["msmType"]
	
	
	print("currDatetime  "+ str(currDatetime))
	print("endDatetime   "+str(endDatetime))
	print("msmIds  "+ str(msmIds))
	print("msmType  "+ str(msmType))
	generateSQLAthenaRequest(currDatetime, endDatetime, currDate, currDate+expParam["timeWindow"], msmIds)
	
		
		
		
        #Getting Items by SQL request
        #result = get_traceroutes_by_version(param={'table': 'traceroutes_7', 'id': '7', 'start': currDate, 'end' : currDate + expParam["timeWindow"]})


        print("currDatetime "+ str(currDatetime))
        """
        start_year= currDatetime.year
        start_month =currDatetime.month
        start_day =currDatetime.day

        end_year = endDatetime.year
        end_month = endDatetime.month
        end_day = endDatetime.day

        two_years=False
        two_month=False
        two_days=False

        if (end_year != start_year ):
            two_years=True

        if end_month != start_month :
            two_month=True
        if end_day != start_day:
            two_days=True

        result=[]
        if end_day == start_day:
            result = get_traceroutes_by_sql_request(
                {'file': 'onedayrequest.sql', 'table': 'traceroutes_api', 'start': currDate, 'day': start_day,
                 'year': start_year,
                 'month': start_month,
                 'end': currDate + expParam["timeWindow"]})

        if end_day != start_day:
            result = get_traceroutes_by_sql_request(
                {'file': 'twodays.sql', 'table': 'traceroutes_api', 'start': currDate,
                 'year': start_year,
                 'month': start_month,
                 'start_day': start_day, 'end_day': end_day,
                 'end': currDate + expParam["timeWindow"]})

        #result = get_traceroutes_by_version(param={'table': 'traceroutes_api',  'start': currDate, 'end' : currDate + expParam["timeWindow"]})


        IRtt, row= rttAnalysisAthenaIteration2.computeRtt_athena(result)
        diffRtt, nbRow = rttAnalysisAthenaIteration2.mergeRttResults_athena(IRtt, row)

        for k, v in diffRtt.iteritems():
            rawDiffRtt[k].extend(v["rtt"])
            rawDates[k].extend([c] * len(v["rtt"]))

        timeSpent = (time.time() - tsS)
        sys.stderr.write(", %s sec/bin,  %s row/sec\r" % (timeSpent, float(nbRow) / timeSpent))
		"""


    pool.close()
    pool.join()




    return (rawDiffRtt, rawNbProbes, rawDates)

