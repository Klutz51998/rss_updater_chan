import requests
import time
import datetime

GET_URL = "https://udiztgv6d4.execute-api.us-east-1.amazonaws.com/prod/news/all?limit=10"
POST_URL = "https://udiztgv6d4.execute-api.us-east-1.amazonaws.com/prod/news/update"
TEAMS_WEBHOOK_URL = (
    "https://ncompasstv.webhook.office.com/webhookb2/"
    "6054878d-e313-4b65-9127-083fac7ddd33@1eaf2bcc-132e-484c-b41a-19f0cb740202/"
    "IncomingWebhook/d969c5ccaffa4573b3e8b96b72693e35/"
    "b989b04e-b645-4e79-9e63-7f4e00f04616/V2kbfWI_Kp3FhwEt0nedxFvk2i_UktBAnYP24tIg0cWh41"
)
 
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Fixed schedule snapped to :00 / :30
SCHEDULE_HOURS   = [0, 5, 9, 14, 19]
SCHEDULE_MINUTES = [0, 0, 30, 30, 0]

'''
Schedule Runs at:

12:00 AM

5:00 AM

9:30 AM

2:30 PM

7:00 PM

'''


def send_to_teams(message: str):
    try:
        payload = {"text": message}
        resp = requests.post(TEAMS_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"⚠️ Failed to send message to Teams: {e}")


def fetch_outdated():
    try:
        resp = requests.get(GET_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Failed to fetch outdated feeds: {e}")
        return []


def fetch_fresh_data(url: str):
    """Fetch the actual RSS/XML content from the feed URL."""
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "rss-updater/1.0"})
        resp.raise_for_status()
        
        return resp.text
        
    except Exception as e:
        print(f"❌ Failed to fetch fresh data from {url}: {e}")
        return None


def update_feed(item, failures=None):
    url = item.get("url")
    
    print(f"{url}")
    
    if not url:
        print("⚠️ Missing URL in item, skipping.")
        return False

    # 🔄 Get fresh data from the feed source
    fresh_data = fetch_fresh_data(url)
    
    if fresh_data is None:
        reason = "Could not fetch fresh feed data"
        failures.append((url, reason))
        return False

    payload = {"Url": url, "Data": fresh_data}
    
    try:
        resp = requests.post(POST_URL, json=payload, headers=HEADERS, timeout=15)

        # ✅ Normalize success check: any 2xx counts as success
        if 200 <= resp.status_code < 300:
            print(f"✅ Updated {url} (status {resp.status_code})")
            return True
        else:
            reason = f"Status {resp.status_code}"
            print(f"❌ Failed {url} | {reason}")
            failures.append((url, reason))
            return False

    except Exception as e:
        reason = str(e)
        print(f"❌ Error updating {url}: {reason}")
        failures.append((url, reason))
        return False



def run_until_empty():
    """
    Keep pulling batches of 10 until:
      - GET returns nothing (all done)
      - or the only remaining items are ones that keep failing
    """
    all_failures = []

    try:
        while True:
            items = fetch_outdated()

            # If API failed and returned nothing
            if not items:
                print("📭 No more outdated feeds.")
                if not all_failures:  # nothing logged yet? mark it as a failure
                    all_failures.append(("system", "No items returned (API timeout or error)"))
                break

            # If we inserted an explicit error marker in fetch_outdated
            if isinstance(items, list) and "error" in items[0]:
                all_failures.append((items[0]["url"], items[0]["error"]))
                break

            print(f"📦 Found {len(items)} outdated feeds")
            failures = []

            for item in items:
                update_feed(item, failures)

            # Retry failures once immediately
            if failures:
                print(f"⚠️ {len(failures)} feeds failed. Retrying once...")
                still_failed = []
                for url, reason in failures:
                    # Let update_feed handle appending to still_failed
                    update_feed({"url": url}, still_failed)

                if still_failed:
                    print(f"🚫 {len(still_failed)} feeds could not be updated.")
                    all_failures.extend(still_failed)
                else:
                    print("✅ All failed feeds succeeded on retry.")

            # If everything in this batch failed, stop (avoid infinite loop)
            if len(failures) == len(items):
                print("🛑 All current items failed. Stopping loop.")
                break

    except Exception as e:
        all_failures.append(("system", f"Crash: {e}"))

# --- TEAMS REPORT ---
    if not all_failures:
        msg = (
            "🌸 Heyya~ FeedFeeder-chan reporting in! 🌸\n\n"
            "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ **RSS Updated Successfully!**\n\n"
            "All the feeds have been taken care of, nice and clean! ✨\n"
            "No gremlins this time — smooth sailing~ 🚀"
        )
    else:
        msg = (
            "🌸 Heyya~ FeedFeeder-chan reporting in! 🌸\n\n"
            "(•﹏•) **RSS Updated (but with some hiccups...)**\n\n"
            f"I tried my best, but {len(all_failures)} feeds didn’t want to behave 🤕\n\n"
            "Here’s the list of the stubborn ones:\n"
            "```\n"
        )
        for url, reason in all_failures:
            msg += f"{url} | {reason}\n"
        msg += "```"

    send_to_teams(msg)


def get_next_run(now=None):
    if now is None:
        now = datetime.datetime.now()

    today = now.date()
    scheduled_times = [
        datetime.datetime.combine(today, datetime.time(h, m))
        for h, m in zip(SCHEDULE_HOURS, SCHEDULE_MINUTES)
    ]

    # Allow a 60-second grace so finishing at 09:30:15 still counts as 09:30
    for t in scheduled_times:
        if -60 <= (t - now).total_seconds() <= 60:
            return t

    # Find the next scheduled time today
    for t in scheduled_times:
        if t > now:
            return t

    # Otherwise, roll over to tomorrow's first slot
    tomorrow = today + datetime.timedelta(days=1)
    return datetime.datetime.combine(
        tomorrow,
        datetime.time(SCHEDULE_HOURS[0], SCHEDULE_MINUTES[0])
    )


def main():
    # Always run once immediately
    print("\nStarting RSS Updater...")
    run_until_empty()

    # Then align to schedule
    while True:
        next_run = get_next_run()
        sleep_seconds = (next_run - datetime.datetime.now()).total_seconds()
        time_str = next_run.strftime('%Y-%m-%d %I:%M %p').replace(" 0", " ")
        print(f"😴 Sleeping until {time_str} ({sleep_seconds/60:.1f} minutes)...")

        time.sleep(sleep_seconds)

        print(f"\n🚀 Scheduled run at {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p').replace(' 0', ' ')}")

        run_until_empty()


if __name__ == "__main__":
    main()
