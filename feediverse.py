#!/usr/bin/env python3

import os
import random
import re
import sys
import yaml
import argparse
import dateutil
import feedparser

from bs4 import BeautifulSoup
from mastodon import Mastodon
from datetime import datetime, timezone, MINYEAR

DEFAULT_CONFIG_FILE = os.path.join("~", ".feediverse")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help=("perform a trial run with no changes made: "
                              "don't toot, don't save config"))
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="be verbose")
    parser.add_argument("-c", "--config",
                        help="config file to use",
                        default=os.path.expanduser(DEFAULT_CONFIG_FILE))

    args = parser.parse_args()
    config_file = args.config

    if args.verbose:
        print("using config file", config_file)

    if not os.path.isfile(config_file):
        setup(config_file)

    config = read_config(config_file)

    masto = Mastodon(
        api_base_url=config['url'],
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        access_token=config['access_token']
    )

    newest_post = config['updated']

    # Content rewrite
    if 'rewrite_source' in config:
        rewrite_source = config['rewrite_source']
    else:
        rewrite_source = []
    if 'rewrite_target' in config:
        rewrite_target = config['rewrite_target']
    else:
        rewrite_target = []

    for feed in config['feeds']:
        feed_url = replace_text(feed['url'], rewrite_source)
        if args.verbose:
            print(f"fetching {feed_url} entries since {config['updated']}")
        # Control whether we use updated or published for time comparison, to avoid spam
        # from fequently updated items, e.g. from YouTube
        if 'time' in config:
            time_type = config['time']
        else:
            time_type = 'updated'
        if time_type not in ['updated', 'published']:
            raise RuntimeError('If set, "time" parameter must be "updated" or "published"')
        # Post visibility
        if 'visibility' in config:
            post_visibility = config['visibility']
        else:
            post_visibility = 'updated'

        if post_visibility not in ['direct', 'private', 'unlisted', 'public']:
            raise RuntimeError('If set, "visibility" parameter must be "direct", "private", "unlisted", or "public"')

        for entry in get_feed(feed_url, time_type, config['updated'], rewrite_target):
            newest_post = max(newest_post, entry['updated'])
            if args.verbose:
                print(entry)
            if args.dry_run:
                print("trial run, not tooting ", entry["title"][:50])
                continue
            masto.status_post(feed['template'].format(**entry)[:499], visibility=post_visibility)

    if not args.dry_run:
        config['updated'] = newest_post.isoformat()
        save_config(config, config_file)

def replace_text(text, replacements):
    """Replace text with random selection from target texts"""

    for replacement in replacements:
        target_index = random.randint(0, len(replacement['targets'])-1)
        text = text.replace(replacement['source'], replacement['targets'][target_index]['text'])
    return text

def get_feed(feed_url, time_type, last_update, replacements):
    feed = feedparser.parse(feed_url)

    # RSS feeds can contain future dates that we don't want to post yet,
    # so we filter them out
    now = datetime.now(timezone.utc)
    entries = [e for e in feed.entries
               if dateutil.parser.parse(e[time_type]) <= now]
    # Now we can filter for date normally
    if last_update:
        entries = [e for e in entries
                   if dateutil.parser.parse(e[time_type]) > last_update]

    entries.sort(key=lambda e: e.updated_parsed)
    for entry in entries:
        yield get_entry(entry, replacements)

def get_entry(entry, replacements):
    hashtags = []
    for tag in entry.get('tags', []):
        t = tag['term'].replace(' ', '_').replace('.', '').replace('-', '')
        hashtags.append('#{}'.format(t))
    summary = entry.get('summary', '')
    content = entry.get('content', '') or ''
    if content:
        content = cleanup(content[0].get('value', ''))
    url = entry.id
    # Fix for Pixelfed Atom that has no published datetime
    if not 'published' in entry:
            entry['published'] = entry['updated']
    return {
        'url': replace_text(url, replacements),
        'link': replace_text(entry.link, replacements),
        'title': replace_text(cleanup(entry.title), replacements),
        'summary': replace_text(cleanup(summary), replacements),
        'content': replace_text(content, replacements),
        'hashtags': ' '.join(hashtags),
        'published': dateutil.parser.parse(entry['published']),
        'updated': dateutil.parser.parse(entry['updated'])
    }

def cleanup(text):
    html = BeautifulSoup(text, 'html.parser')
    text = html.get_text()
    text = re.sub('\xa0+', ' ', text)
    text = re.sub('  +', ' ', text)
    text = re.sub(' +\n', '\n', text)
    text = re.sub('\n\n\n+', '\n\n', text, flags=re.M)
    return text.strip()

def find_urls(html):
    if not html:
        return
    urls = []
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(["a", "img"]):
        if tag.name == "a":
            url = tag.get("href")
        elif tag.name == "img":
            url = tag.get("src")
        if url and url not in urls:
            urls.append(url)
    return urls

def yes_no(question):
    res = input(question + ' [y/n] ')
    return res.lower() in "y1"

def save_config(config, config_file):
    copy = dict(config)
    with open(config_file, 'w') as fh:
        fh.write(yaml.dump(copy, default_flow_style=False))

def read_config(config_file):
    config = {
        'updated': datetime(MINYEAR, 1, 1, 0, 0, 0, 0, timezone.utc)
    }
    with open(config_file) as fh:
        cfg = yaml.load(fh, yaml.SafeLoader)
        if 'updated' in cfg:
            cfg['updated'] = dateutil.parser.parse(cfg['updated'])
    config.update(cfg)
    return config

def setup(config_file):
    url = input('What is your Mastodon Instance URL? ')
    have_app = yes_no('Do you have your app credentials already?')
    if have_app:
        name = 'feediverse'
        client_id = input('What is your app\'s client id: ')
        client_secret = input('What is your client secret: ')
        access_token = input('access_token: ')
    else:
        print("Ok, I'll need a few things in order to get your access token")
        name = input('app name (e.g. feediverse): ')
        client_id, client_secret = Mastodon.create_app(
            api_base_url=url,
            client_name=name,
            #scopes=['read', 'write'],
            website='https://github.com/edsu/feediverse'
        )
        username = input('mastodon username (email): ')
        password = input('mastodon password (not stored): ')
        m = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=url)
        access_token = m.log_in(username, password)

    feed_url = input('RSS/Atom feed URL to watch: ')
    old_posts = yes_no('Shall already existing entries be tooted, too?')
    config = {
        'name': name,
        'url': url,
        'time': 'updated',
        'visibility': 'unlisted',
        'client_id': client_id,
        'client_secret': client_secret,
        'access_token': access_token,
        'feeds': [
            {'url': feed_url, 'template': '{title} {url}'}
        ]
    }
    if not old_posts:
        config['updated'] = datetime.now(tz=timezone.utc).isoformat()
    save_config(config, config_file)
    print("")
    print("Your feediverse configuration has been saved to {}".format(config_file))
    print("Add a line line this to your crontab to check every 15 minutes:")
    print("*/15 * * * * /usr/local/bin/feediverse")
    print("")

if __name__ == "__main__":
    main()
