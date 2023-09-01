#-*- coding: utf-8 -*-

from flask import Flask
from flask_restx import Api, Resource
import boto3
from boto3.dynamodb.conditions import Attr

# Set up API Keys and names
aws_access_key_id = "<AWS_ACCESS_KEY_ID>"
aws_secret_access_key = "<AWS_SECRET_ACCESS_KEY>"
region_name = "<REGION_NAME>"
dynamodb_table_name = "<DYNAMODB_NAME>"

# set up important variables
dynamodb = boto3.resource('dynamodb',
                        aws_access_key_id = aws_access_key_id,
                        aws_secret_access_key = aws_secret_access_key,
                        region_name = region_name)
table = dynamodb.Table(dynamodb_table_name)

app = Flask(__name__)
api = Api(app)


# Returns the number of active workers
@api.route('/numactiveworkers')
class NumActiveWorkers(Resource):
    def get(self):
        response = table.scan(
            FilterExpression=Attr('status').eq('downloading')
        )
        items = response['Items']
        return "Number of active workers: " + str(len(items))


# Returns the total number of videos downloaded and filtered for each query
@api.route('/numdownloadedandfiltered')
class NumDownloadedAndFiltered(Resource):
    def get(self):
        response = table.scan()

        # set that keeps track of query values
        queries = set([])
        
        # add queries to the set
        for item in response['Items']:
            queries.add(item['query'])

        # get number of videos downloaded and filtered for each query
        return_dict = {}
        for query in queries:
            response = table.scan(
                FilterExpression = Attr('query').eq(query)&Attr('status').eq('done')
            )
            down_num = len(response["Items"])
        
            response = table.scan(
                FilterExpression = Attr('query').eq(query)&Attr('filtered_condition').eq('filtered out')
            )
            filtered_num = str(len(response['Items']))
            return_dict[query] = {"download" : down_num, "filtered" : filtered_num}
        return return_dict


# Returns the average download speed (MB/s) for each worker
@api.route('/averagedownloadspeed')
class AverageDownloadSpeed(Resource):
    def get(self):
        response = table.scan(
            FilterExpression=Attr('status').eq('done')
        )
        return_list = []
        for item in response["Items"]:
            video_id = item["video_id"]
            download_speed = item["download_speed"]
            file_size = item["file_size"]
            return_list.append({"video_id" : video_id, "download_speed" : download_speed, "file_size" : file_size})
        return return_list


# Returns the current video being downloaded by each worker
@api.route('/currentvideo')
class CurrentVideo(Resource):
    def get(self):
        response = table.scan(
            FilterExpression=Attr('status').eq('downloading')
        )
        return_list = []
        for item in response["Items"]:
            video_id = item["video_id"]
            status = item["status"]
            return_list.append({"video_id" : video_id, "status" : status})
        return return_list

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)