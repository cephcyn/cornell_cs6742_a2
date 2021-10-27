import urllib.request
import json
import pandas as pd
import numpy as np
import time
from datetime import datetime, date
import argparse

# An export of data_collection.ipynb (as of 2021/10/26)

def scrape_subreddit(subreddit_name, scrape_year):
    # checkpoint output
    print(f'scraping subreddit: {subreddit_name}')
    print(f'    data from year: {scrape_year}')
    print(f' scrape START time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    t0 = time.process_time()
    scrape_begin = datetime(scrape_year, 1, 1)
    scrape_end = datetime(scrape_year+1, 1, 1)
    
    # do the submissions scrape
    with urllib.request.urlopen(
        f'https://api.pushshift.io/reddit/search/submission/'
        +f'?subreddit={subreddit_name}&after={int(scrape_begin.timestamp())}&before={int(scrape_end.timestamp())}'
    ) as url:
        data = json.loads(url.read().decode())
    data = data['data']
    df_sub = pd.DataFrame.from_dict(pd.json_normalize(data), orient='columns')
    
    # checkpoint output
    print(f' == submissions collected, starting comments')
    print(f'           at time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    print(f'   so-far DURATION: {time.process_time() - t0}')
    
    # do the comments ID scrape
    def get_comment_ids(sub_id):
        with urllib.request.urlopen(
            f'https://api.pushshift.io/reddit/submission/comment_ids/{sub_id}'
        ) as url:
            data = json.loads(url.read().decode())
        print(sub_id)
        return data['data']
    df_sub['comments'] = [get_comment_ids(x) for x in df_sub['id']]
    
    # checkpoint output
    print(f' == comments collected, starting comment detail')
    print(f'           at time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    print(f'   so-far DURATION: {time.process_time() - t0}')
    
    # do the comments scrape
    df_comm = pd.DataFrame()
    for comment_id_list in df_sub['comments']:
        print(comment_id_list)
        with urllib.request.urlopen(
            f'https://api.pushshift.io/reddit/search/comment/?ids={",".join(comment_id_list)}'
        ) as url:
            data = json.loads(url.read().decode())
        df_comm = df_comm.append(pd.DataFrame.from_dict(pd.json_normalize(data['data'])))
            
    # checkpoint output
    print(f'   scrape END time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    print(f'    total DURATION: {time.process_time() - t0}')
    
    return df_sub, df_comm

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--subreddit', required=True, help='Subreddit to scrape posts from')
    parser.add_argument('--output_post', required=False, default='output_post.csv', help='file (CSV) to save raw post data to')
    parser.add_argument('--output_comment', required=False, default='output_comment.csv', help='file (CSV) to save raw comment data to')
    parser.add_argument('--year', type=int, required=True, help='Year to scrape data during')
    args = parser.parse_args()
    df_sub, df_comm = scrape_subreddit(args.subreddit, args.year)
    df_sub.to_csv(args.output_post)
    df_comm.to_csv(args.output_comment)