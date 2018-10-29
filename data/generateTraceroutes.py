import json


rtt1=[1, 2, 1, 3]
rtt2=[60,555,498,6000]
rtt3=[0.2,0.1,0.2,0.1]
rtt4=[1, 2, 1, 3]
rtt5=[1, 2, 1, 3]
rtt6=[1, 2, 1, 3]
rtt7=[60,55,98,60]
rtt8=[60,85,98,80]
rtt9=[680,845,998,800]
rtt10=[680,845,998,800]
rtt11=[10680,10845,10998,10800]
rtt12=[1060,1045,1098,1080]
rtt13=[1060,1045,1098,1080]
rtt14=[1, 2, 1, 3]
rtt15=[1, 2, 1, 3]
rtt16=[100, 267, 156, 324]
rtt17=[10980, 26887, 15786, 32467]
rtt18=[10989, 26889, 15789, 32460]
rtt19=[989, 26889, 15789, 32460]
rtt20=[5000,4566,8768,879]
rtt21=[1, 2, 1, 3]
rtt22=[10, 20, 10, 30]
rtt23=[12, 21, 41, 38]
rtt24=[7, 2, 4, 3]
rtt25=[1, 2, 4, 3]

allrtts=[
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
rtt1,
 rtt1
]

def generateTraceroutes(traceroute="traceroute.json"):
    print "debut "
    result= open('result.json', 'w')

    #read traceroute on a json object
    trace=None

    if True:
        i = 1
        for rtt1 in allrtts:
            for rtt in rtt1:
                with open(traceroute) as t:
                    tmptrace = json.load(t)
                tmptrace["result"][1]['result'][0]['rtt'] = tmptrace["result"][1]['result'][0]['rtt']+ rtt
                tmptrace["result"][1]['result'][1]['rtt'] = tmptrace["result"][1]['result'][1]['rtt']+ rtt
                tmptrace["result"][1]['result'][2]['rtt'] = tmptrace["result"][1]['result'][2]['rtt']+ rtt
                tmptrace["timestamp"] = tmptrace["timestamp"] + int(3600) * int(i)
                newTraceroute = json.dumps(tmptrace)
                result.write("%s\n"%newTraceroute)
            i=i+1


    result.close()






tracerouteJson =generateTraceroutes()
#print(tracerouteJson['from'])
