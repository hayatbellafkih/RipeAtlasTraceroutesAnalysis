
import sys
import json
import numpy as np
from collections import defaultdict
from get_all_traceroutes import fetchall_athena
import tools
import boto3
try:
    import smtplib
    from email.mime.text import MIMEText
    import emailConf
except ImportError:
    pass


#sys.path.append("../lib/ip2asn/")
#import ip2asn

config=tools.get_properties()

def readOneTraceroute(trace, diffRtt, metric=np.nanmedian):
    """Read a single traceroute instance and compute the corresponding
    differential RTTs.
    """

    if trace is None or "error" in trace["result"][0] or "err" in trace["result"][0]["result"]:
        return diffRtt

    probeIp = trace["from"]
    probeId = None
    msmId = None
    if "prb_id" in trace:
        probeId = trace["prb_id"]
    if "msm_id" in trace:
        msmId = trace["msm_id"]
    prevRttMed = {}

    for hopNb, hop in enumerate(trace["result"]):
        try:
            # TODO: clean that workaround results containing no IP, e.g.:
            # {u'result': [{u'x': u'*'}, {u'x': u'*'}, {u'x': u'*'}], u'hop': 6},

            if "result" in hop :

                rttList = defaultdict(list)
                rttMed = {}

                for res in hop["result"]:
                    if not "from" in res  or tools.isPrivateIP(res["from"]) or not "rtt" in res or res["rtt"] <= 0.0:
                        continue

                    # assert hopNb+1==hop["hop"] or hop["hop"]==255

                    rttList[res["from"]].append(res["rtt"])

                print (rttList)
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


def readOneTraceroutePersonalisedAllSignals( trace, diffRtt, metric=np.nanmedian):
    #[{"from2":"192.168.15.1", "rtt1":1.38, "from":"173.160.35.54", "from1":"192.168.15.1", "rtt2":1.173, "msm_id":1026355, "from3":"192.168.15.1", "prb_id":2567, "hop":1, "rtt3":1.179}, {"from2":"10.1.10.1", "rtt1":3.304, "from":"173.160.35.54", "from1":"10.1.10.1", "rtt2":5.495, "msm_id":1026355, "from3":"10.1.10.1", "prb_id":2567, "hop":2, "rtt3":4.704}, {"from2":"96.120.12.125", "rtt1":14.281, "from":"173.160.35.54", "from1":"96.120.12.125", "rtt2":18.292, "msm_id":1026355, "from3":"96.120.12.125", "prb_id":2567, "hop":3, "rtt3":24.442}, {"from2":"162.151.15.213", "rtt1":11.217, "from":"173.160.35.54", "from1":"162.151.15.213", "rtt2":14.393, "msm_id":1026355, "from3":"162.151.15.213", "prb_id":2567, "hop":4, "rtt3":12.217}, {"from2":"68.86.179.237", "rtt1":24.482, "from":"173.160.35.54", "from1":"68.86.179.237", "rtt2":14.541, "msm_id":1026355, "from3":"68.86.179.237", "prb_id":2567, "hop":5, "rtt3":16.972}, {"from2":"4.68.63.165", "rtt1":24.866, "from":"173.160.35.54", "from1":"4.68.63.165", "rtt2":14.534, "msm_id":1026355, "from3":"4.68.63.165", "prb_id":2567, "hop":6, "rtt3":34.351}, {"from2":"4.69.153.150", "rtt1":154.366, "from":"173.160.35.54", "from1":"4.69.153.150", "rtt2":164.354, "msm_id":1026355, "from3":"4.69.153.150", "prb_id":2567, "hop":7, "rtt3":160.011}, {"from2":"212.73.203.18", "rtt1":193.559, "from":"173.160.35.54", "from1":"212.73.203.18", "rtt2":164.347, "msm_id":1026355, "from3":"212.73.203.18", "prb_id":2567, "hop":8, "rtt3":157.141}, {"from2":"193.171.23.41", "rtt1":189.509, "from":"173.160.35.54", "from1":"193.171.23.41", "rtt2":164.334, "msm_id":1026355, "from3":"193.171.23.41", "prb_id":2567, "hop":9, "rtt3":185.547}, {"from2":"193.170.114.242", "rtt1":156.01, "from":"173.160.35.54", "from1":"193.170.114.242", "rtt2":164.126, "msm_id":1026355, "from3":"193.170.114.242", "prb_id":2567, "hop":10, "rtt3":155.468}]

    """Read a single traceroute instance and compute the corresponding
    differential RTTs.
    """


    print(trace)
    traceroute = trace[0].encode('ascii', 'ignore')
    print(trace)
    sys.exit(0)
    entry = traceroute
    entry = entry.replace("=", ":")
    data = json.loads(entry.decode('string-escape').strip('"'))
    trace=data
    #print(trace)
    if trace is None or   trace[0]["error"] is not None or  trace[0]["err1"] is not None:
        return diffRtt



    probeIp = trace[0]['from']
    probeId = None
    msmId = None
    if "prb_id" in trace[0]:
        probeId = trace[0]["prb_id"]

    if "msm_id" in trace[0]:
        msmId = trace[0]["msm_id"]
    prevRttMed = {}

    for  hop in (trace):
        try:
            # TODO: clean that workaround results containing no IP, e.g.:
            # {u'result': [{u'x': u'*'}, {u'x': u'*'}, {u'x': u'*'}], u'hop': 6},

            if True :

                rttList = defaultdict(list)
                rttMed = {}

                for i in range(3):
                    #print( hop["rtt%d"%(i+1)])
                    if not "from%d"%(i+1) in hop  or hop["from%d"%(i+1)] is None or tools.isPrivateIP(hop["from%d"%(i+1)]) or not "rtt%d"%(i+1) in hop or hop["rtt%d"%(i+1)] <= 0.0:
                        #print("fail")
                        continue

                    # assert hopNb+1==hop["hop"] or hop["hop"]==255


                    rttList[hop["from%d"%(i+1)]].append(hop["rtt%d"%(i+1)])



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
    #print(diffRtt)
    return diffRtt
def get_data(file_path= config['DEFAULT']['un_traceroute']):
    with open(file_path) as f:
        for line in f:
            j_content = json.loads(line)
    return j_content

if __name__ == "__main__":
    # Get RTT details from mongoDB
    sample= get_data()
    print(sample)
    diffRtt={}
    readOneTraceroute(sample, diffRtt)
    print(diffRtt)

    # Get RTT details from athena

    sql_request_athena = tools.load_sql_request_by_file("sql_step_1.sql")
    try:
        client = boto3.client("athena", region_name='eu-west-1')
        resultats = fetchall_athena(sql_request_athena, client)
        data=[]
        for result in  resultats:
            for element in  result:
                data.append({'med': float(result[0]), 'from' : str(result[1]), 'hop': int(result[2])})
            print result
        print data
    except Exception as e:
        print("apparently table not exist !", e.args, e.message)
        print []
