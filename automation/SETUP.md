# WordPress Daily Poster — Setup Guide

Posts one queued article per day to a WordPress.com site via the public
REST API, saved as a **draft** for your review. You publish manually.
Use it like this: configure a WordPress.com site in config.json, queue articles, and run the poster once a day. Example site: your-site.wordpress.com.

## Example: post a series of articles to any domain

Here is how you can post to any domain a series of articles. No code
changes are needed — the domain is a variable, not hard-coded.

1. Copy `config.example.json` to `config.json` and set `site` to any
   domain you own. Example:
   ```json
   {"site": "your-site.wordpress.com", "status": "draft"}
   ```
   In other words: `site` is the variable. Replace the example domain
   with your own domain, and the poster posts to that domain.
2. Put a series in `queue/`, one file per article, in order:
   `01-first-article.md`, `02-second-article.md`, `03-third-article.md`.
   Each file starts with `TITLE: <title>`, a blank line, then HTML.
3. Dry-run first, then run once a day:
   ```sh
   python3 post_article.py --dry-run
   python3 post_article.py
   ```
   Each run posts the lowest-numbered queued article, moves it to
   `posted/`, and records it in `state.json`, so a series posts one
   article per run, in order, to the domain in `config.json`.

## Files

- `post_article.py` — the poster. Reads the next queued article, posts it,
  verifies the post exists (by title, tolerant of WordPress's typographic
  substitutions), moves the file to `posted/`, and records it in `state.json`.
- `config.example.json` — copy to `config.json` and set your site:
  `{"site": "your-site.wordpress.com", "status": "draft"}`.
  Use `"publish"` only if you want posts to go live immediately.

## Queue format

Create a `queue/` directory next to the script. Each article is one
Markdown file, `NN-slug.md`:

```
TITLE: Your Article Title

<h2>First section</h2>
<p>Body HTML goes here...</p>
```

First line `TITLE:`, blank line, then the HTML body. The poster takes the
lowest-numbered file first.

## Token (the only secret, and it stays yours)

The poster reads a WordPress.com OAuth2 bearer token from a file named
`.wp_token` next to the script (chmod 600). It is **never** committed —
this repo ships no token, no state, and no drafts.

To get one:

1. Create an app at https://developer.wordpress.com/apps — type **Web**,
   description of your choice, redirect URL `https://example.com/`
   (the form requires a redirect URL and rejects ones containing
   "WordPress", so `example.com` is the practical placeholder).
2. Open the authorize URL with your app's client ID:
   `https://public-api.wordpress.com/oauth2/authorize?client_id=<YOUR_CLIENT_ID>&redirect_uri=https://example.com/&response_type=token`
3. Approve, then copy the `access_token` fragment out of the redirect URL
   (URL-decode it) into `.wp_token`.
4. Verify: `curl -H "Authorization: Bearer $(cat .wp_token)" https://public-api.wordpress.com/rest/v1.1/me`
   should show your display name.

Tokens last 14 days (`expires_in=1209600`). Re-authorize the same way when
one lapses; the daily run reports an auth failure instead of retrying
blindly, so a lapsed token can never double-post.

## Running it daily

```sh
python3 post_article.py            # post the next queued article
python3 post_article.py --dry-run  # parse the next article, show what would post
```

Schedule it however you like — cron, Task Scheduler, or a hosted runner —
once a day. Keep the queue topped up (3+ articles is a comfortable buffer);
the poster does not write articles, it only posts what you queued.

## Failure behavior (deliberate)

- If the POST response is cut off mid-read (`IncompleteRead`) or
  unparseable, the script **verifies by title** against the recent draft
  and publish listings before recording anything. It raises instead of
  recording if the post is not found — so a network hiccup can never
  silently double-post or silently drop an article.
- Verification reads are retried a few times with sleeps; they are
  read-only and safe to retry.
