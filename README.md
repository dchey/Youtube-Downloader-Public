# Youtube-Downloader

<!-- ABOUT THE PROJECT -->
## About the Project
1. Youtube video collection pipeline that downloads videos with multiprocessing + filtering, and uploading certain videos to AWS S3 Bucket + logging important stats to AWS DynamoDB.
2. Backend API server for reporting metrics for the pipeline.

### Built With
* Python
* Flask
* AWS S3 Bucket + DynamoDB
* Youtube API
* yt-dlp

### Resources
* AWS S3 Bucket : https://aws.amazon.com/s3/
* AWS DynamoDB : https://aws.amazon.com/pm/dynamodb/
* Youtube API : https://developers.google.com/youtube/v3
* yt-dlp documentation : https://github.com/yt-dlp/yt-dlp
 * yt-dlp installation : https://www.youtube.com/watch?v=L7GcjfTNRvA

## Getting Started
### Prerequisites
Highly recommend setting up a virtual environment. Install virtualenv with this code below:
```bash
python3 -m pip install --user virtualenv
```

Go to the project directory and run venv, which will create a virtual Python installation in the env folder:
```bash
python3 -m venv env
```

Run this code to activate the virtual environment:
```bash
source env/bin/activate
```

Run this to deactivate:
```bash
deactivate
```

### Installation
In the project directory, install the required libraries in requirements.txt file:
```bash
pip3 install -r requirements.txt
```

### Project Structure
* `youtube.py` : code for Youtube video collection pipeline.
* `monitor.py` : code for Backend API server.
* `Download/` : folder that contains downloaded videos from the pipeline

### Update API Keys and AWS tool names
In youtube.py and monitor.py, set up the names of API keys and bucket/table names:
* youtube_api_key = "<YOUTUBE_API_KEY>"
* aws_access_key_id = "<AWS_ACCESS_KEY_ID>"
* aws_secret_access_key = "<AWS_SECRET_ACCESS_KEY>"
* s3_bucket_name = "<S3_BUCKET_NAME>"
* region_name = "<REGION_NAME>"
* dynamodb_table_name = "<DYNAMODB_NAME>" 

## Executing the Program
### Youtube video collection pipeline (youtube.py)
This part downloads 30 raw videos of the top 30 search results given a list of search query (like ["son heung min", "ryu hyun jin"]) with multiprocessing, uploads videos that satisfy these conditions below to the S3 Bucket, and logs relevant statistics of this process to DynamoDB.
1. Video length between 8 and 12 minutes.
2. Video resolution in 720p.
3. Video format in .mp4.
4. Video contains Audio.

To execute this process, run this code below in the project directory folder:
```bash
python3 youtube.py "query_1" "query_2" "..."
```
where "query_#" is the query term you want to search for.


### Backend API server (monitor.py)
This part runs a backend API server that monitors the status of the collection pipeline with these statistics:
1. Number of active workers.
2. Total number of videos downloaded and filtered for each query.
3. Average download speed (MB/s) for each worker.
4. Current video being downloaded by each worker.

To execute this process, run this code below in the project directory folder
```bash
python3 monitor.py
```
and go to this link below to monitor the statistics:
```
http://127.0.0.1:3000/
```

If you want a better monitoring view, run this code below after running the above code:
```bash
watch -n 1 curl 127.0.0.1:3000/<statistics>
```
Where you replace statistics with one of these options for one of the four statistics being monitored:
1. `numactiveworkers` : Number of active workers.
2. `numdownloadedandfiltered` : Total number of videos downloaded and filtered for each query.
3. `averagedownloadspeed` : Average download speed (MB/s) for each worker.
4. `currentvideo` : Current video being downloaded by each worker.