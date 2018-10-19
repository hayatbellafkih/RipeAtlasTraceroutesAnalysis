#imports
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tools import get_properties
import boto3
import time


#GET DETAILS FOR EACH REQUEST

FILENAME_REQUEST="select_traceroutes_from.sql"
FILENAME_CONFIG="CONFIG.ini"


def fetchall_athena(query_string, client):

    config_athena= get_properties(FILENAME_CONFIG)
    database=config_athena['default']['database']
    output_athena=config_athena['default']['OutputLocation']

    query_id = client.start_query_execution(
        QueryString=query_string,
        QueryExecutionContext={
            'Database': database
        },
        ResultConfiguration={
            'OutputLocation': output_athena
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





