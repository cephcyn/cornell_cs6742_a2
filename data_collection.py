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

# An export of data_collection.ipynb (as of 2021/10/31)

def scrape_subreddit_posts(subreddit_name, scrape_year, backup_pkl_in=None, backup_pkl_out=None):
    # checkpoint output
    print(f'scraping subreddit: {subreddit_name}')
    print(f'    data from year: {scrape_year}')
    print(f' scrape START time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}', flush=True)
    t0 = time.process_time()
    scrape_begin = int(datetime(scrape_year, 1, 1).timestamp())
    scrape_end = int(datetime(scrape_year+1, 1, 1).timestamp())
    
    # load from backup if available
    if (backup_pkl_in is not None) and exists(backup_pkl_in):
        df_sub = pd.read_pickle(backup_pkl_in)
        created_utc_now_sub = df_sub_new.tail(1)['created_utc']
        current_start = int(created_utc_now_sub + 1)
        print(f'Loaded checkpoint: {backup_pkl_in}')
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
            if backup_pkl_out is not None:
                df_sub.to_pickle(backup_pkl_out)
                print(f'Saved checkpoint: {backup_pkl_out}')
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
    if backup_pkl_out is not None:
        df_sub.to_pickle(backup_pkl_out)
    return df_sub


def scrape_post_comments(subreddit_name, df_sub):
    # checkpoint output
    print(f'scraping given batch of posts for comment list')
    print(f' scrape START time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}', flush=True)
    t0 = time.process_time()
    
    # do the comments ID scrape
    comment_ids = []
    for sub_id in df_sub['id']:
        with urllib.request.urlopen(
            f'https://api.pushshift.io/reddit/submission/comment_ids/{sub_id}'
        ) as url:
            data = json.loads(url.read().decode())
        comment_ids.append(data['data'])
        if len(comment_ids)%50==0:
            print(f'got comments from these many posts so far: {len(comment_ids)}', flush=True)
    df_sub['comments'] = comment_ids
    print(f'should have {sum([len(x) for x in comment_ids])} comments total')
            
    # checkpoint output
    print(f'   scrape END time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}')
    print(f'    total DURATION: {time.process_time() - t0}', flush=True)
    
    # return scraped data
    df_sub = df_sub.reset_index(drop=True)
    return df_sub


def scrape_full_comments(subreddit_name, df_sub, backup_pkl_in=None, backup_pkl_out=None):
    # checkpoint output
    print(f'scraping given batch of posts for comment details')
    print(f' scrape START time: {time.strftime("%Y%m%d-%H%M%S", time.localtime())}', flush=True)
    t0 = time.process_time()
    
    # load from backup if available
    if (backup_pkl_in is not None) and exists(backup_pkl_in):
        df_comm = pd.read_pickle(backup_pkl_in)
        print(f'Loaded checkpoint: {backup_pkl_in}')
    else:
        df_comm = pd.DataFrame()
        print(f'Started from scratch')
    
    # do the comments detail scrape
    TEMP=0
    for sub in df_sub.index:
        sub_id = df_sub.loc[sub]['id']
        sub_comms = df_sub.loc[sub]['comments']
        if ('link_id' in df_comm) and (f't3_{sub_id}' in [str(e) for e in df_comm['link_id']]):
            continue
        keep_commscraping = len(sub_comms)>0
        current_start = 1
        comms_so_far = 0
        mini_comm = pd.DataFrame()
        while keep_commscraping:
            try:
                TEMP+=1
                if TEMP>=5:
                    raise Exception('I know Python!')
                with urllib.request.urlopen(
                    f'https://api.pushshift.io/reddit/comment/search/'
                    +f'?limit=1000&sort=asc&link_id={sub_id}&after={current_start}'
                ) as url:
                    data = json.loads(url.read().decode())
            except Exception as e:
                print('EXCEPTION HAPPENED:')
                print(e, flush=True)
                if backup_pkl_out is not None:
                    df_comm.to_pickle(backup_pkl_out)
                    print(f'Saved checkpoint: {backup_pkl_out}')
                sys.exit()
            if ('data' in data) and len(data['data'])>0:
                data = data['data']
                mini_comm_new = pd.DataFrame.from_dict(pd.json_normalize(data), orient='columns')
                mini_comm = mini_comm.append(mini_comm_new)
                created_utc_now_comm = mini_comm_new.tail(1)['created_utc']
                current_start = int(created_utc_now_comm + 1)
                print(f'new batch comments count: {mini_comm_new.shape[0]}, next scanning {current_start}-?', flush=True)
                comms_so_far += max(500, mini_comm_new.shape[0])
                keep_commscraping = (comms_so_far < len(sub_comms))
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
    if backup_pkl_out is not None:
        df_comm.to_pickle(backup_pkl_out)
    return df_comm


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--subreddit', required=True, help='Subreddit to scrape posts from')
    parser.add_argument('--year', type=int, required=True, help='Year to scrape data during')
    args = parser.parse_args()
    
    # do post scrapes
    if not exists(f'{args.year}_posts_draft.pkl'):
        backup_posts = f'{args.year}_01_backup.pkl'
        df_sub = scrape_subreddit_posts(args.subreddit, args.year, backup_pkl_in=backup_posts, backup_pkl_out=backup_posts)
        # export checkpoint scrapes
        df_sub.to_csv(f'{args.year}_posts_draft.csv')
        df_sub.to_pickle(f'{args.year}_posts_draft.pkl')
        # df_sub.to_hdf(f'{args.year}_posts_draft.h5', key=f'data')
    else:
        df_sub = pd.read_pickle(f'{args.year}_posts_draft.pkl')
    
    # do per-post comment list scrapes
    if not exists(f'{args.year}_posts.pkl'):
        df_sub = scrape_post_comments(args.subreddit, df_sub)
        # export checkpoint scrapes
        df_sub.to_csv(f'{args.year}_posts.csv')
        df_sub.to_pickle(f'{args.year}_posts.pkl')
        # df_sub.to_hdf(f'{args.year}_posts.h5', key=f'data')
    else:
        df_sub = pd.read_pickle(f'{args.year}_posts.pkl')
    
    # do comment detail scrapes
    if not exists(f'{args.year}_comments.pkl'):
        backup_posts = f'{args.year}_02_backup.pkl'
        df_comm = scrape_full_comments(args.subreddit, df_sub, backup_pkl_in=backup_posts, backup_pkl_out=backup_posts)
        # export checkpoint scrapes
        df_comm.to_csv(f'{args.year}_comments.csv')
        df_sub.to_pickle(f'{args.year}_comments.pkl')
        # df_comm.to_hdf(f'{args.year}_comments.h5', key=f'data')
