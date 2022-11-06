*feediverse* will read RSS/Atom feeds and send the messages as Mastodon posts.
It's meant to add a little bit of spice to your timeline from other places.
Please use it responsibly.

## Install

    pip install feediverse

## Run

The first time you run *feediverse* you'll need to tell it your Mastodon
instance and get an access token which it will save in a configuration file. If
you don't specify a config file it will use `~/.feediverse`:

    feediverse

Once *feediverse* is configured you can add it to your crontab:

    */15 * * * * /usr/local/bin/feediverse

Run `feediverse --help` to show the command line options.

## Tracking Updated vs. Published datetime

By default, the time comparison for fetching posts is done from the `updated` RSS tag.
If you need to change this to avoid spam from frequently updates items (e.g. from YouTube),
you can change this with the property

    time: published

This can only be done per configuration file, not per feed.

# Visibility

By default, posts will be unlisted. To change this, use the configuration property `visibility`, e.g.

    visibility: public

Available values are documented in the
[Mastodon upstream project](https://github.com/halcy/Mastodon.py/blob/master/mastodon/Mastodon.py).


# Content Warnings

You can CW all posts by adding the parameter:

    cw: Spoiler Text

# Rewriting URLs

The rewrite options can be used e.g. to swap links in the posts for more privacy-friendly options,
or for load balancing on the feed source.
Specify 1 source and multiple targets for random selection.
Examples for using [Invidious instances](https://docs.invidious.io/instances/) instead of YouTube in posts:

```
rewrite_target:
- source: https://www.youtube.com/
  targets:
  - text: https://invidious.snopyta.org/
  - text: https://yewtu.be/
  - text: https://invidious.kavin.rocks/
  - text: https://invidious.namazso.eu/
  - text: https://invidious.osi.kr/
  - text: https://yt.artemislena.eu/
  - text: https://tube.cthd.icu/
  - text: https://invidious.flokinet.to/
```

And load balancing while sourcing from [Nitter instances](https://xnaas.github.io/nitter-instances/):

```
rewrite_source:
- source: https://nitter.net/
  targets:
  - text: https://nitter.sethforprivacy.com/
  - text: https://nitter.pussthecat.org/
  - text: https://nitter.nixnet.services/
  - text: https://nitter.namazso.eu/
  - text: https://bird.trom.tf/
  - text: https://nitter.grimneko.de/
  - text: https://nitter.mstdn.social/
  - text: https://nitter.weiler.rocks/
  - text: https://tw.artemislena.eu/
  - text: https://de.nttr.stream/
  - text: https://nitter.privacy.com.de/
  - text: https://nitter.notraxx.ch/
  - text: https://nitter.lunar.icu/
  - text: https://nitter.tiekoetter.com/
```

## Post Format

You can customize the post format by opening the configuration file (default is
~/.feediverse) and updating the *template* property of your feed. The default
format is:

    {title} {url}

If you want you can use `{summary}` in your template, and add boilerplate text
like so:

    Bookmark: {title} {url} {summary}

`{hashtags}` will look for tags in the feed entry and turn them into a space
separated list of hashtags. For some feeds (e.g. youtube-rss) you should use `{link}` instead of `{url}`.

`{content}` is the whole content of the feed entry (with html-tags
stripped). Please be aware that this might easily exceed Mastodon's
limit of 512 characters.

## Multiple Feeds

Since *feeds* is a list you can add additional feeds to watch if you want.

    ...
    feeds:
      - url: https://example.com/feed/
        template: "dot com: {title} {url}"
      - url: https://example.org/feed/
        template: "dot org: {title} {url}"

