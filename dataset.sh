conda activate cs6742_a2

python data_collection.py --subreddit amitheasshole --year 2018 > 2018_log.txt 2>&1 #&
python data_collection.py --subreddit amitheasshole --year 2019 > 2019_log.txt 2>&1 #&

