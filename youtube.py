#-*- coding: utf-8 -*-
# used to deal with non-english letters in Youtube API

import os
import sys
from yt_dlp import YoutubeDL
import multiprocessing
import boto3
from googleapiclient.discovery import build
from isodate import parse_duration
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)

# Set up API Keys and names
youtube_api_key = "<YOUTUBE_API_KEY>"
aws_access_key_id = "<AWS_ACCESS_KEY_ID>"
aws_secret_access_key = "<AWS_SECRET_ACCESS_KEY>"
s3_bucket_name = "<S3_BUCKET_NAME>"
region_name = "<REGION_NAME>"
dynamodb_table_name = "<DYNAMODB_NAME>"


# Important variables
max_results_per_query = 30

# Set up Youtube API, S3 Bucket, and DynamoDB Table
youtube = build('youtube', 'v3', developerKey=youtube_api_key)
s3 = boto3.client('s3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name)
dynamoDB = boto3.resource('dynamodb',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name)
dynamodb_table = dynamoDB.Table(dynamodb_table_name)




def search_top_30(query):
    """
    Function that uses the YouTube API search function to collect the Top 30 videos of the given query input.
    Check the link below for more information about the YouTube API search function:
    https://developers.google.com/youtube/v3/docs/search

    :param query: input query for searching videos on YouTube
    :return: a list of video IDs representing the top 30 search results of the query
    """ 
    try:
        # Use the YouTube API search method to retrieve video data based on the given query
        search_response = youtube.search().list(
            q=query, # The search query term
            type='video', # Retrieve only videos (options: video, channel, playlist)
            order='rating', # Sort search results by rating, highest to lowest (options: date, rating, relevance, title, videoCount, viewCount)
            eventType='completed', # Do not search live or upcoming videos (options: live, upcoming, completed)
            maxResults=max_results_per_query, # The maximum number of items to be returned
            part='id,snippet' # Required data parts: id (video ID) and snippet (video details)
            ).execute()
    except:
        # Raise unexpected error when searching youtube videos: live videos -> upcoming case
        raise Exception("Unexpected error occurred while searching")
    
    # Extract video IDs from search_response and store them in a list
    video_ids = [item['id']['videoId'] for item in search_response['items']]
    
    # Make sure the number of videos searched is correct
    if len(video_ids) != max_results_per_query:
        raise Exception("The number of items searched is incorrect")
    
    # Return the list of video IDs representing the top 30 search results
    return video_ids



def filter_video(video_ids):
    """
    Function that categorizes videos into ones that passed the filter and ones that did not.
    Filter condition:
        1. Videos between 8-12 minutes long
        2. Videos with 720p resolution
    
    Check the link below for more information about the Youtube API videos function:
    https://developers.google.com/youtube/v3/docs/videos
    
    :param video_ids: a list of video IDs to be filtered
    :return: a tuple containing two lists - one with video IDs that passed the filter and another with video IDs that did not
    """
    
    # Lists to store video IDs that passed the filter and those that did not
    filter_passed_video_ids = []
    filter_out_video_ids = []

    # Filtering process for each video ID
    for video_id in video_ids:
        # Retrieve video information using the YouTube API videos method
        video_information = youtube.videos().list(part='contentDetails', id=video_id).execute()

        # Extract relevant information from video_information
        definition = video_information["items"][0]["contentDetails"]["definition"]
        duration = video_information["items"][0]["contentDetails"]["duration"]
        duration_in_seconds = parse_duration(duration).total_seconds()
        
        # Check if the video meets the filter conditions
        if 480 <= duration_in_seconds <= 720 and definition == "hd":
            filter_passed_video_ids.append(video_id)
        else:
            filter_out_video_ids.append(video_id)
    
    # Make sure the sum of number of videos filtered is equal to the length of video_ids
    if len(filter_passed_video_ids) + len(filter_out_video_ids) != len(video_ids):
        raise Exception("The number of items filtered is incorrect")
    
    # Return a tuple containing the lists of video IDs that passed and did not pass the filter
    return filter_passed_video_ids, filter_out_video_ids



def download_video(video_id, query):
    """
    Function that downloads videos in .mp4 format with audio and also log conditions of the download 
    process in DynamoDB.
    Check the link below for more information about yt-dlp package:
    https://github.com/yt-dlp/yt-dlp 
    
    :param video_ids: a list of video IDs to be downloaded
    :param query: query term used to search for the video
    :return: none
    """
    
    # Update status and start_time in dynamodb_table
    start_time = datetime.now()
    
    dynamodb_table.update_item(
        Key={
            'query': query, # Partition Key
            'video_id': str(video_id), # Sort Key
        },
        AttributeUpdates={
            'status' : {
                'Value': 'downloading', # Set status to downloading
                'Action': 'PUT'
            },
            'start_time' : {
                'Value': str(start_time), # Set the end time of the downloading process
                'Action': 'PUT'
            }
        }
    )
    
    ydl_opts = {
        "format": "b[height=720][ext=mp4]/mp4+b[height=720]/b", # Download format options
        "outtmpl": os.path.join("Download", query, f"{video_id}.%(ext)s") # File directory = Download/"query_name"/"video_id".mp4
    }
    
    # Use yt-dlp to download the video
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(["https://www.youtube.com/watch?v=" + video_id])
    
    
    
    # Calculate download speed in MB/s
    end_time = datetime.now()
    file_size = round(os.path.getsize("Download/"+query+"/"+video_id+".mp4") / (1024.0 * 1024.0), 1)
    time_passed_in_sec = (end_time - start_time).seconds
    download_speed = round(file_size / time_passed_in_sec, 2)
    
    # Update status, end_time, file_size, and download_speed in DynamoDB Table
    dynamodb_table.update_item(
        Key={
            'query': query, # Partition Key
            'video_id': str(video_id), # Sort Key
        },
        AttributeUpdates={
            'status' : {
                'Value': 'done', # Set status to done
                'Action': 'PUT'
            },
            'end_time' : {
                'Value': str(end_time), # Set the end time of the downloading process
                'Action': 'PUT'
            },
            'file_size' : {
                'Value': str(file_size), # Insert the file size of the downloaded video file
                'Action': 'PUT'
            },
            'download_speed' : {
                'Value': str(download_speed), # Insert the download speed of the progress in MB/s
                'Action': 'PUT'
            }
        }
    )


def upload_to_s3(video_id, query):
    """
    Function that uploads videos to s3 bucket.

    :param video_id: video ID of videos to be uploaded to the S3 Bucket
    :param query: The query term used to search for the videos
    :return: None
    """
    
    # Notification about videos being uploaded to the s3 bucket
    logging.info("Start uploading " + video_id + " in " + query + " folder to s3 bucket")
    
    # Initialize variable for file names in local directory and s3 bucket
    local_file = "Download/"+query+"/"+video_id+".mp4" # location of the downloaded video in local directory
    file_name_in_s3 = query+"/"+video_id+".mp4" # file name stored in s3 = "query_name"/"video_id".mp4
    
    # Upload the video to s3 bucket
    s3.upload_file(local_file, s3_bucket_name, file_name_in_s3)
    
    # Notification about videos that were successfully uploaded to the s3 bucket
    logging.info("Successfully uploaded "+ video_id + " to " + query + " folder in s3 bucket")




def work_processes(query):
    """
    Work process function of multiprocessing.

    :param query: The query term to be processed in the above functions
    :return: None
    """    
    # Notification that multiprocessing worker has started
    logging.info("Work started for: " + query)
    
    # 1. Search for top 30 videos for each query
    top_30_video_ids = search_top_30(query)
    
    # 2. Apply filter to the top 30 searches and display the number of videos that passed the filter and those that were filtered out
    filter_passed_video_ids, filter_out_video_ids = filter_video(top_30_video_ids)
    logging.info("Number of videos passed the filter for " + query + " : " + str(len(filter_passed_video_ids)))
    logging.info("Number of videos filter out for " + query + " : " + str(len(filter_out_video_ids)))
    
    
    # 3. Initialize the status of the downloading process to DynamoDB Table
    for video_id in top_30_video_ids:
        # Check whether the given video_id has been filtered
        if video_id in filter_passed_video_ids:
            filtered_condition = 'filter passed'
        elif video_id in filter_out_video_ids:
            filtered_condition = 'filtered out'
        else:
            logging.warning("video_id %s warning: filtered condition not known" %video_id)
            filtered_condition = 'unknown'
        
        # Set up dynamodb_table
        dynamodb_table.put_item(
            Item={
                'query': query, # Query term (Partition Key)
                'video_id': str(video_id), # Video ID (Sort Key)
                'status' : 'standing by', # Set the status to standing by
                'filtered_condition': filtered_condition, # Set the filtered_condition
                'start_time': '',
                'end_time': '',
                'download_speed': '',
                'file_size' : ''
            }
        )
    
    # 4. Download all 30 videos for each query and log conditions of download process in DynamoDB
    for id in top_30_video_ids:
        download_video(id, query)
    
    # 5. Upload filtered videos to the s3 bucket
    for id in filter_passed_video_ids:
        upload_to_s3(id, query)
    
    # Notification that multiprocessing worker has finished working
    logging.info("--------------- Work completeted for: " + query + "---------------")


def main():
    """
    Main call of this file.
    """
    
    # Save downloaded videos in download folder
    os.makedirs('Download', exist_ok=True)
    
    # Check the command-line arguments, making sure there is at least one query
    if len(sys.argv) > 1:
        search_queries = sys.argv[1:]
    else:
        logging.warning("Please provide search queries as command-line arguments.")
        sys.exit(1)    
    
    # Sets the number of processes to 3 if the number of queries in query list is 3 or less.
    # Else set it to the smaller value between the number of queries and cpu count
    num_processes = 3 if len(search_queries) <= 3 else min(len(search_queries), multiprocessing.cpu_count())
    
    
    # Multiprocessing implementation
    logging.info("----------------------- Multiprocessing begins with number of processes = " + str(num_processes) + " -----------------------")
    pool = multiprocessing.Pool(processes=num_processes)
    pool.map(work_processes, search_queries)
    pool.close()
    pool.join()


if __name__ == "__main__":
    main()