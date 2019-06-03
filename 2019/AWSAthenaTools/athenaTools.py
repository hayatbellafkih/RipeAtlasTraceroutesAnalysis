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
import tools
import matplotlib.pylab as plt
import statsmodels.api as sm

#constants
AWS_CONFIG = "AwsConfig.ini"

#Find aws configuration
config = ConfigParser.ConfigParser()
config.readfp(open(AWS_CONFIG))
print(config)

secret= config.get("default", "aws_access_key_id")
access= config.get("default", "aws_secret_access_key")
region = config.get("athena", "region")

def load_sql_request_by_file(filename=''):
	"""
	Read and return the generic SQL request
	:param filename:
	:return:

	"""

	try:
		request_file= open(filename, 'r')
	except IOError:
		print "Could not read file:", filename
		sys.exit()

	request= request_file.readline()

	return request

def generateSQLAthenaRequest (start, end,currentTimestamp, endTimestamp, msmIds=[]) :

	"""

	Create and return  SQL request in Amazon Athena

	:param start: start date
	:param end:   end dat
	:param currentTimestamp: start t
	:param endTimestamp:
	:param msmIds:
	:return:
	"""

	print ("Start creation SQL request to the given timewindow")
	delta = end - start
	ors = list()
	
	#add dates

	#add msm Ids only if are defined
	nbMsmIds= len(msmIds)

	print ("%d measuremet id found "% nbMsmIds)
	if nbMsmIds >0:
	#add measurement Ids
		msm=""
		i= 0
		while i<  nbMsmIds-1:
			msm=   "%s msm= '%s' OR "%(msm, msmIds[i])
			i=i+1
		msm = "%s msm = '%s' "%(msm, msmIds[i])
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
	else:
		#do not add measurement Ids, add only partitions about date
		for i in range(delta.days + 1):
			tmpDate = start + timedelta(i)
			partialPartSqlRequest= "(year = '%s' and month = '%s' and day = '%s' )"%(tmpDate.year, tmpDate.month, tmpDate.day)
			ors.append(partialPartSqlRequest)

		total = len(ors)
		count = 0
		s="("
		while( count < total -1):
			s= s + ors[count] + " OR "
			count =count + 1
			
		s= s+  ors[count] + ")"		


	#load general request and add parameters
	print ("Start formating  the SQL request ...")
	sqlRequest= load_sql_request_by_file("sqlRequestForAthena.sql")
	finalRequest= sqlRequest.format( currentTimestamp, endTimestamp, s)
	return finalRequest


def computeRtt_athena( (alltraceroutes) ):

    """
    Process each traceroute in alltraceroutes. alltraceroutes are the traceroutes for a given period
    """
    nbRow = 0
    diffRtt = defaultdict(dict)

    cursor=[]
    for trace in alltraceroutes:
        readOneTracerouteAllSigna(trace, diffRtt)
        nbRow += 1


    return diffRtt, nbRow


def readOneTracerouteAllSigna(trace, diffRtt, metric=np.nanmedian):
    """Read a single traceroute instance and compute the corresponding
    differential RTTs.
    """


    traceroute=[element.encode('ascii', 'ignore')  for element in trace]
    data=str(trace[3].encode('ascii', 'ignore'))
    entry = data.replace("=", ":")
    data = json.loads(entry.decode('string-escape').strip('"'))


    if len(data) ==0:
        return diffRtt

    probeIp = str(trace[0].encode('ascii', 'ignore'))
    probeId = int(trace[1].encode('ascii', 'ignore'))
    msmId = str(trace[2].encode('ascii', 'ignore'))
    if probeId is not None:
        probeId = int(trace[1].encode('ascii', 'ignore'))
    else:
        probeId =None
    if msmId is not None:
        msmId = str(trace[2].encode('ascii', 'ignore'))
    else:
        msmId=None
    prevRttMed = {}

    #print('data ',data)
    for hopNb, hop in enumerate(data):
        try:
            # TODO: clean that workaround results containing no IP, e.g.:
            # {u'result': [{u'x': u'*'}, {u'x': u'*'}, {u'x': u'*'}], u'hop': 6},
            rttList = defaultdict(list)
            rttMed = {}

            for element    in hop:
                ipadress = element.keys()[0]
                rtt = element[ipadress]
                if tools.isPrivateIP(ipadress) or  rtt <= 0.0 :
                    continue

                # assert hopNb+1==hop["hop"] or hop["hop"]==255
                rttList[ipadress].append(rtt)

            for ip2, rtts in rttList.iteritems():
                    rttAgg = np.median(rtts)
                    rttMed[ip2] = rttAgg

                    # Differential rtt
                    if len(prevRttMed):
                        for ip1, pRttAgg in prevRttMed.iteritems():
                            if ip1 == ip2 :
                                continue

                            # data for (ip1, ip2) and (ip2, ip1) are put
                            # together in mergeRttResults
                            if not (ip1, ip2) in diffRtt:
                                diffRtt[(ip1,ip2)] = {"rtt": [],
                                                        "probe": [],
                                                        "msmId": defaultdict(set)
                                                        }

                            i = diffRtt[(ip1,ip2)]
                            i["rtt"].append(rttAgg-pRttAgg)
                            i["probe"].append(probeIp)
                            i["msmId"][msmId].add(probeId)
        finally:
            prevRttMed = rttMed
            # TODO we miss 2 inferred links if a router never replies


    return diffRtt


def mergeRttResults_athena(iRtt, compRows):
    print("debut mergeRttResults_athena")
    diffRtt = defaultdict(dict)
    nbRow = 0
    if compRows == 0:
        return
    i=1
    if not iRtt is None:
        for k, v in iRtt.iteritems():
            #print("v = %s" % (str(v)))
            #print("k = %s" % (str(k)))

            # put together data for (ip1, ip2) and (ip2, ip1)
            ipPair = tuple(sorted(k))
            if ipPair in diffRtt:
                inf = diffRtt[ipPair]
                inf["rtt"].extend(v["rtt"])
                inf["probe"].extend(v["probe"])
                for msmId, probes in v["msmId"].iteritems():
                    inf["msmId"][msmId].update(probes)
            else:
                diffRtt[ipPair] = v

    nbRow += compRows
    print("nbRow=%s "%nbRow)
    return diffRtt, nbRow


def get_traceroutes_by_sql_request( final_request=""):
	print("Start get_traceroutes_by_sql_request : "+ str())
	start = time.time()
	client = boto3.client("athena", region_name =region,
	aws_access_key_id='yours',
	aws_secret_access_key='yours'	)
	resultat = fetchall_athena(final_request, client)
	end = time.time()
	print("Total Time is "+ str(end - start))
	print ("Total results is %d "%len(resultat))

	return resultat



def fetchall_athena(query_string, client):
    config_athena= get_confuration_by_file(AWS_CONFIG)
    database=get_value_property(config_athena,'athena', 'database')
    output_athena=get_value_property(config_athena,'athena', 'OutputLocation')
    query_id = client.start_query_execution(
        QueryString=query_string,
        QueryExecutionContext={
            'Database': database
        },
        ResultConfiguration={
            'OutputLocation': 's3://athenaresultsfromripatlasdata/'
        }
    )['QueryExecutionId']
    query_status = None
    while query_status == 'QUEUED' or query_status == 'RUNNING' or query_status is None:
        query_status = client.get_query_execution(QueryExecutionId=query_id)['QueryExecution']['Status']['State']
        if query_status == 'FAILED' or query_status == 'CANCELLED':
            raise Exception('Athena query with the string "{}" failed or was cancelled'.format(query_string))
        time.sleep(10)
    results_paginator = client.get_paginator('get_query_results')
    results_iter = results_paginator.paginate(
        QueryExecutionId=query_id,
        PaginationConfig={
            'PageSize': 1000
        }
    )
    results = []
    data_list = []
    for results_page in results_iter:
        for row in results_page['ResultSet']['Rows']:
            data_list.append(row['Data'])
    for datum in data_list[1:]:
        results.append([x['VarCharValue'] for x in datum])
    return results
    # return [str(x).encode('ascii', 'ignore') for x in results]


def get_confuration_by_file(path_file_config=""):

    if os.path.isfile(path_file_config):
        config = ConfigParser.ConfigParser()
        config.read(path_file_config)
        return  config
    else:
        print("File %s not exist !"%path_file_config)
        return


def get_value_property(config= None,section='', key=''):
    """
    DO NOT change CONFIGS.ini
    :return:
    """
    try:
        return config.get(section,key)

    except Exception as e:
        print(e.args)

def getRttDataAthena(configFile=None):

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



	for currDate in range(start, end, expParam["timeWindow"]):

		sys.stderr.write("Rtt analysis %s" % datetime.datetime.utcfromtimestamp(currDate))
		tsS = time.time()

		diffRtt = defaultdict(dict)
		nbRow = 0

		currDatetime= datetime.datetime.utcfromtimestamp(int(currDate))
		endDatetime= datetime.datetime.utcfromtimestamp(int(currDate+int(expParam["timeWindow"])))
		msmIds= expParam["msmIds"]
		msmType=  expParam["msmType"]


		# Prepare the SQL request for the given period
		sqlRequest = generateSQLAthenaRequest(currDatetime, endDatetime, currDate, currDate+expParam["timeWindow"], msmIds)

		print ("The created SQL request is : \n %s"%sqlRequest)


		# Find Results
		result = get_traceroutes_by_sql_request(sqlRequest)
		if len(result)>0 :
			IRtt, row= computeRtt_athena(result)

			diffRtt, nbRow = mergeRttResults_athena(IRtt, row)

			for k, v in diffRtt.iteritems():
				rawDiffRtt[k].extend(v["rtt"])
				rawDates[k].extend([currDatetime] * len(v["rtt"]))

			timeSpent = (time.time() - tsS)
			sys.stderr.write(", %s sec/bin,  %s row/sec\r" % (timeSpent, float(nbRow) / timeSpent))


	pool.close()
	pool.join()
	return (rawDiffRtt, rawNbProbes, rawDates)


def rttEvolution(res, ips, suffix):
    finaleData={}
    finaleData["link"]= ips
    ipNames = {
            "193.0.14.129": "K-root",
            "80.81.192.154": "RIPE NCC @ DE-CIX",
            "61.213.160.62": "NTT, Tokyo",
            "72.52.92.14": "HE, Frankfurt",
            "74.208.6.124": "1&1, Kansas City",
            "212.191.229.90": "Poznan, PL",
            "188.93.16.77": "Selectel, St. Petersburg",
            "95.213.189.0": "Selectel, Moscow",
            "130.117.0.250": "Cogent, Zurich",
            "154.54.38.50": "Cogent, Munich",
            }

    rttDiff = np.array(res)
    smoothAvg = []
    smoothHi = []
    smoothLow = []
    alarmsDates = []
    alarmsValues = []
    median = []
    mean = []
    ciLow = []
    ciHigh = []
    dates = []

    start = np.min(rttDiff[1])
    end = np.max(rttDiff[1])
    diff = end-start


    dateRange = [start+timedelta(hours=x) for x in range((diff.days+1)*24)]

    for d in dateRange:
        indices = rttDiff[1]==d  
        dist = rttDiff[0][indices]
        if len(dist) < 3:
            continue
        dates.append(d)
        median.append(np.median(dist))
        mean.append(np.mean(dist))
        dist.sort()
        wilsonCi = sm.stats.proportion_confint(len(dist)/2, len(dist), 0.05, "wilson")
        wilsonCi = np.array(wilsonCi)*len(dist)
        ciLow.append( median[-1] - dist[int(wilsonCi[0])] )
        ciHigh.append( dist[int(wilsonCi[1])] - median[-1] )
        if len(smoothAvg)<3:
            smoothAvg.append(median[-1])
            smoothHi.append(dist[int(wilsonCi[1])])
            smoothLow.append(dist[int(wilsonCi[0])])
        elif len(smoothAvg)==3:
            smoothAvg.append(np.median(smoothAvg))
            smoothHi.append(np.median(smoothHi))
            smoothLow.append(np.median(smoothLow))
            for i in range(3):
                smoothAvg[i] = smoothAvg[-1]
                smoothHi[i] = smoothHi[-1]
                smoothLow[i] = smoothLow[-1]
        else:
            smoothAvg.append(0.99*smoothAvg[-1]+0.01*median[-1])
            smoothHi.append(0.99*smoothHi[-1]+0.01*dist[int(wilsonCi[1])])
            smoothLow.append(0.99*smoothLow[-1]+0.01*dist[int(wilsonCi[0])])

            if (median[-1]-ciLow[-1] > smoothHi[-1] or median[-1]+ciHigh[-1] < smoothLow[-1]) and np.abs(median[-1]-smoothAvg[-1])>1:
                alarmsDates.append(d)
                alarmsValues.append(median[-1])



    finaleData["dates"]= dates
    finaleData["alarmsDates"]= alarmsDates
    finaleData["alarmsValues"]= alarmsValues
    finaleData["reference"]= {"valueMedian" : smoothAvg, "valueHi" : smoothHi, "valueLow" : smoothLow }
    finaleData["current"]= {"valueMedian" : median, "valueHi" : ciHigh , "valueLow" : ciLow}

    if len(median)<2:
        return 0

    # uncomment these lines to create  graphics	
    """
    fig = plt.figure(figsize=(10,3))
    boundref = plt.fill_between(dates, smoothLow, smoothHi, color="#3333cc", facecolor="#DDDDFF", label="Normal Reference")
    # Workarround to have the fill_between in the legend
    boundref = plt.Rectangle((0, 0), 1, 1, fc="#DDDDFF", color="#3333cc")
    medianref, = plt.plot(dates, smoothAvg, '-', color="#AAAAFF")
    # plt.plot(dates, smoothHi, 'k--')
    # plt.plot(dates, smoothLow, 'k--')
    data = plt.errorbar(dates, median, [ciLow, ciHigh], fmt=".", ms=7, color="black", ecolor='0.33',  elinewidth=1, label="Diff. RTT")
    ano, = plt.plot(alarmsDates, alarmsValues, "r*", ms=10, label="Anomaly")
    plt.grid(True, color="0.75")
    # if ips[0] in ipNames and ips[1] in ipNames:
        # plt.title("%s (%s) - %s (%s)" % (ips[0],ipNames[ips[0]],ips[1],ipNames[ips[1]]))
    # else:
        # plt.title("%s - %s" % ips)
    fig.autofmt_xdate()
    if len(alarmsValues):
        plt.legend([data, (boundref, medianref), ano],["Median Diff. RTT", "Normal Reference", "Detected Anomalies"], loc="best")
    else:
        plt.legend([data, (boundref, medianref)],["Median Diff. RTT", "Normal Reference"], loc="best")
    plt.ylabel("Differential RTT (ms)")
    # plt.yscale("log")
    plt.tight_layout()
    plt.savefig("fig/diffRtt/%s_%s_%sAlarms_rttModel.eps" % (ips[0].replace(".","_"), ips[1].replace(".","_"), len(alarmsDates)))
    plt.close()

    f, ax = plt.subplots(1,1,figsize=(3.2,2.4))
    plt.ylim([-4, 4])
    plt.xlim([-4, 4])
    sm.qqplot(np.array(median), line="45", fit=True, ax=ax)
    # plt.title("Median")
    plt.grid(True, color="0.75")
    plt.ylabel("Median diff. RTT quantiles")
    plt.xlabel("Normal theoretical quantiles")
    plt.ylim([-4, 4])
    plt.xlim([-4, 4])
    plt.tight_layout()
    plt.savefig("fig/diffRtt/%s_%s_%sAlarms_qqplot_median.eps" % (ips[0].replace(".","_"), ips[1].replace(".","_"), len(alarmsDates)))
    plt.close()

    f, ax = plt.subplots(1,1,figsize=(3.2,2.4))
    sm.qqplot(np.array(mean), line="45", fit=True, ax=ax)
    # plt.title("Mean")
    plt.grid(True, color="0.75")
    plt.ylabel("Mean diff. RTT quantiles")
    plt.xlabel("Normal theoretical quantiles")
    plt.tight_layout()
    plt.savefig("fig/diffRtt/%s_%s_%sAlarms_qqplot_mean.eps" % (ips[0].replace(".","_"), ips[1].replace(".","_"), len(alarmsDates)))
    plt.close()


    plt.figure()
    plt.hist(rttDiff[0], bins=150)
    plt.grid(True, color="0.75")
    plt.yscale("log")
    plt.savefig("fig/diffRtt/%s_%s_distributionSamples.eps" % (ips[0].replace(".","_"), ips[1].replace(".","_")))
    plt.close()

    # fig = plt.figure(figsize=(10,4))
    fig = plt.figure(figsize=(20,2.5))
    plt.plot(rttDiff[1], rttDiff[0],"o",label="Raw values",ms=1)
    plt.grid(True)
    # plt.yscale("log")
    dat = np.array(rttDiff[0])
    m = np.mean(dat)
    s = np.std(dat)
    o = np.sum((dat>m+3*s) | (dat<m-3*s))
    operc = o/float(len(dat))

    # plt.title("%s - %s (mean=%.02f, std=%.02f, outliers=%s %.02f%%)" % (ips[0], ips[1], m, s, o, operc))
    plt.ylabel("Differential RTT (ms)")
    if ips[0] in ipNames and ips[1] in ipNames:
        plt.title("%s (%s) - %s (%s)" % (ips[0],ipNames[ips[0]],ips[1],ipNames[ips[1]]))
    else:
        plt.title("%s - %s" % ips)
    plt.legend( loc="best")
    plt.ylim([100,300])
    plt.xticks([])
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.savefig("fig/diffRtt/%s_%s_samples.eps" % (ips[0].replace(".","_"), ips[1].replace(".","_")))
    plt.close()
    """
    return finaleData


