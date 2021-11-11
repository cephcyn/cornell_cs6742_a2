import urllib.request
import json
import pandas as pd
import numpy as np
import time
from datetime import datetime, date
import argparse
import sys
import pickle
from os.path import exists

# An export of data_collection.ipynb (as of 2021/11/11)

def scrape_subreddit_posts(subreddit_name, scrape_year, backup_fname_in=None, backup_fname_out=None):
    # checkpoint output
    print(f'scraping subreddit: {subreddit_name}')
    print(f'    data from year: {scrape_year}')
    print(f' scrape START time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}', flush=True)
    t0 = time.process_time()
    scrape_begin = int(datetime(scrape_year, 1, 1).timestamp())
    scrape_end = int(datetime(scrape_year+1, 1, 1).timestamp())
    
    # load from backup if available
    if (backup_fname_in is not None) and exists(f'{backup_fname_in}.csv'):
        df_sub = pd.read_csv(f'{backup_fname_in}.csv')
        created_utc_now_sub = df_sub.tail(1)['created_utc']
        current_start = int(created_utc_now_sub + 1)
        print(f'Loaded checkpoint: {backup_fname_in}.csv')
    else:
        current_start = scrape_begin
        df_sub = pd.DataFrame()
        print(f'Started from scratch')
    
    # do the submissions scrape
    keep_subscraping = True
    while keep_subscraping:
        try:
            with urllib.request.urlopen(
                f'https://api.pushshift.io/reddit/search/submission/'
                +f'?limit=1000&sort=asc&subreddit={subreddit_name}&after={current_start}&before={scrape_end}'
            ) as url:
                data = json.loads(url.read().decode())
        except Exception as e:
            print('EXCEPTION HAPPENED:')
            print(e, flush=True)
            if backup_fname_out is not None:
                df_sub.to_csv(f'{backup_fname_out}.csv', index=False)
                print(f'Saved checkpoint: {backup_fname_out}.csv')
            sys.exit()
        if ('data' in data) and len(data['data'])>0:
            data = data['data']
            df_sub_new = pd.DataFrame.from_dict(pd.json_normalize(data), orient='columns')
            df_sub = df_sub.append(df_sub_new)
            created_utc_now_sub = df_sub_new.tail(1)['created_utc']
            current_start = int(created_utc_now_sub + 1)
            print(f'new batch submissions count: {df_sub_new.shape[0]}, next scanning {current_start}-{scrape_end}', flush=True)
            time.sleep(1)
        else:
            keep_subscraping = False
            
    # checkpoint output
    print(f'   scrape END time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    print(f'    total DURATION: {time.process_time() - t0}', flush=True)
    
    # return scraped data
    df_sub = df_sub.reset_index(drop=True)
    if backup_fname_out is not None:
        df_sub.to_csv(f'{backup_fname_out}.csv', index=False)
    return df_sub


def scrape_full_comments(subreddit_name, df_sub, backup_fname_in=None, backup_fname_out=None):
    # checkpoint output
    print(f'scraping given batch of posts for comment details')
    print(f' scrape START time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}', flush=True)
    t0 = time.process_time()
    
    # load from backup if available
    if (backup_fname_in is not None) and exists(f'{backup_fname_in}.csv'):
        df_comm = pd.read_csv(f'{backup_fname_in}.csv')
        print(f'Loaded checkpoint: {backup_fname_in}.csv')
    else:
        df_comm = pd.DataFrame()
        print(f'Started from scratch')
    
    # do the comments detail scrape
    for sub in df_sub.index:
        sub_id = df_sub.loc[sub]['id']
        num_comms = df_sub.loc[sub]['num_comments']
        if ('link_id' in df_comm) and (f't3_{sub_id}' in [str(e) for e in df_comm['link_id']]):
            continue
        keep_commscraping = num_comms>0
        current_start = 1
        comms_so_far = 0
        mini_comm = pd.DataFrame()
        while keep_commscraping:
            try:
                with urllib.request.urlopen(
                    f'https://api.pushshift.io/reddit/comment/search/'
                    +f'?limit=1000&sort=asc&link_id={sub_id}&after={current_start}'
                ) as url:
                    data = json.loads(url.read().decode())
            except Exception as e:
                print('EXCEPTION HAPPENED:')
                print(e, flush=True)
                if backup_fname_out is not None:
                    df_comm.to_csv(f'{backup_fname_out}.csv', index=False)
                    print(f'Saved checkpoint: {backup_fname_out}.csv')
                sys.exit()
            if ('data' in data) and len(data['data'])>0:
                data = data['data']
                mini_comm_new = pd.DataFrame.from_dict(pd.json_normalize(data), orient='columns')
                mini_comm = mini_comm.append(mini_comm_new)
                created_utc_now_comm = mini_comm_new.tail(1)['created_utc']
                current_start = int(created_utc_now_comm + 1)
                print(f'new batch comments count: {mini_comm_new.shape[0]}, next scanning {current_start}-?', flush=True)
                comms_so_far += max(500, mini_comm_new.shape[0])
                keep_commscraping = (comms_so_far < num_comms)
                time.sleep(1)
            else:
                keep_commscraping = False
        df_comm = df_comm.append(mini_comm)
        print(f'finished indexing comments from one submission', flush=True)
    print(f'comments count {df_comm.shape[0]}')
            
    # checkpoint output
    print(f'   scrape END time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    print(f'    total DURATION: {time.process_time() - t0}', flush=True)
    
    # return scraped data
    df_comm = df_comm.reset_index(drop=True)
    if backup_fname_out is not None:
        df_comm.to_csv(f'{backup_fname_out}.csv', index=False)
    return df_comm


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--subreddit', required=True, help='Subreddit to scrape posts from')
    parser.add_argument('--year', type=int, required=True, help='Year to scrape data during')
    args = parser.parse_args()
    
    # do post scrapes
    if not exists(f'{args.year}_posts.csv'):
        backup_posts = f'{args.year}_01_backup'
        df_sub = scrape_subreddit_posts(args.subreddit, args.year, backup_fname_in=backup_posts, backup_fname_out=backup_posts)
        # export checkpoint scrapes
        df_sub.to_csv(f'{args.year}_posts.csv', index=False)
        # df_sub.to_hdf(f'{args.year}_posts.h5', key=f'df')
        # df_sub.to_pickle(f'{args.year}_posts.pkl')
    else:
        df_sub = pd.read_csv(f'{args.year}_posts.csv')
    
    # do comment detail scrapes
    if not exists(f'{args.year}_comments.csv'):
        backup_posts = f'{args.year}_02_backup'
        df_comm = scrape_full_comments(args.subreddit, df_sub, backup_fname_in=backup_posts, backup_fname_out=backup_posts)
        # export checkpoint scrapes
        df_comm.to_csv(f'{args.year}_comments.csv', index=False)
        # df_comm.to_hdf(f'{args.year}_comments.h5', key=f'df')
        # df_comm.to_pickle(f'{args.year}_comments.pkl')
