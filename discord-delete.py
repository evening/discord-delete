import configparser
import requests
import sys
import time

# from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import (confirm, ProgressBar)
from prompt_toolkit.styles import Style

config = configparser.ConfigParser()
config.read("account.ini")
s = requests.Session()
s.headers, base = (
    {"Authorization": config["Settings"]["auth_key"]},
    "https://discordapp.com/api/v8",
)


def convert_dm_rid(uid):
    """Find DM channel ID based on user ID"""
    for channel in s.get(f"{base}/users/@me/channels").json():
        if channel["type"] == 1 and channel["recipients"][0]["id"] == uid:
            return channel["id"]
    return uid


def main():
    params = {k: v for k, v in config["Params"].items() if v}
    params.update({"author_id": s.get(f"{base}/users/@me").json()["id"]})
    resource_id = config["Settings"]["resource_id"]

    if config["Settings"]["type"] in ("server", "guilds"):
        resource_type = "guilds"
    elif config["Settings"]["type"] in ("DM", "channels"):
        resource_id = convert_dm_rid(resource_id)
        resource_type = "channels"
    else:
        sys.exit("set `type` to either `server` or `DM`")

    to_delete = f"messages in {get_title(resource_type, resource_id)}"
    if not confirm(f"Delete {to_delete}?"):
        sys.exit()
    with ProgressBar(
        title=f"Deleting {to_delete}",
        style=Style.from_dict({"bottom-toolbar": "noreverse"}),
    ) as pb:
        num_messages = s.get(
            f"{base}/{resource_type}/{resource_id}/messages/search", params=params
        ).json()["total_results"]
        for msg, p in zip(
            messages(resource_type, resource_id, params), pb(range(num_messages)),
        ):
            delete(msg, pb)


def messages(res, rid, params):
    r = s.get(f"{base}/{res}/{rid}/messages/search", params=params)
    if r.status_code == 200:
        msgs = r.json()["messages"]
        recovered = False
        for msg in msgs:
            entry = [*filter(lambda x: x.get("hit"), msg)][0]
            if entry["type"] != 3:
                recovered = True
                yield entry
            del msg
        if recovered:
            yield from messages(res, rid, params)
    elif r.status_code == 429:
        t = r.json()["retry_after"]
        time.sleep(t)
        messages(res, rid, params)
    elif r.status_code >= 400:
        sys.exit(r.status_code, r.json())


def delete(msg, pb):
    # https://discord.com/developers/docs/reference#snowflakes
    d = time.gmtime(((int(msg["id"]) >> 22) + 1_420_070_400_000) / 1000)
    r = s.delete(f"{base}/channels/{msg['channel_id']}/messages/{msg['id']}")
    if r.status_code == 429:
        t = r.json()["retry_after"]
        pb.bottom_toolbar = f"Limited: {t}"
        time.sleep(t)
        delete(msg, pb)
    elif r.status_code >= 400:
        sys.exit(r.status_code, r.json())
    else:
        pb.bottom_toolbar = f"{d.tm_mon}/{d.tm_mday}/{d.tm_year} {msg['content']}"
        time.sleep(0.15)


def get_title(res, sid):
    username = s.get(f"{base}/users/@me").json()["username"]
    r = s.get(f"{base}/{res}/{sid}").json()
    if res == "guilds":
        return f"{r['name']} by {username}"
    elif res == "channels":
        return f"{r['recipients'][0]['username']} by {username}"


if __name__ == "__main__":
    main()
