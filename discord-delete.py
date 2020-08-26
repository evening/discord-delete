import configparser
import requests
import sys
import time

config = configparser.ConfigParser()
config.read("account.ini")
s = requests.Session()
s.headers, base = (
    {"Authorization": config["Settings"]["auth_key"]},
    "https://discordapp.com/api/v6",
)


def convert_dm_rid(uid):
    """Find DM channel ID based on user ID"""
    for channel in s.get(f"{base}/users/@me/channels").json():
        if channel["type"] == 1 and channel["recipients"][0]["id"] == uid:
            return channel["id"]
    return uid


def main():
    user_id = s.get(f"{base}/users/@me").json()["id"]
    resource_id = config["Settings"]["resource_id"]

    params = {k: v for k, v in config["Params"].items() if v}
    params.update({"author_id": user_id})

    if config["Settings"]["type"] in ("server", "guilds"):
        resource_type = "guilds"
    elif config["Settings"]["type"] in ("DM", "channels"):
        resource_id = convert_dm_rid(resource_id)
        resource_type = "channels"
    else:
        sys.exit("set `type` to either `server` or `DM`")
        
    info(resource_type, resource_id)
    for c, msg in enumerate(messages(resource_type, resource_id, params), 1):
        # https://discord.com/developers/docs/reference#snowflakes
        d = time.gmtime(((int(msg["id"]) >> 22) + 1_420_070_400_000) / 1000)
        print(c, f"{d.tm_mon}/{d.tm_mday}/{d.tm_year}", repr(msg["content"]))
        delete(msg)


def messages(res, rid, params):
    r = s.get(f"{base}/{res}/{rid}/messages/search", params=params)
    code = r.status_code
    if code == 200:
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
    elif code == 429:
        t = r.json()["retry_after"]
        print("Limited", code, t)
        time.sleep(t / 950)
    elif code >= 400:
        print(f"Error", code, r.text)


def delete(msg):
    r = s.delete(f"{base}/channels/{msg['channel_id']}/messages/{msg['id']}")
    code = r.status_code
    if code == 429:
        t = r.json()["retry_after"]
        print("Limited", code, t)
        time.sleep(t / 950)
    elif code >= 400:
        print("Error", code, r.text)
    else:
        time.sleep(0.15)


def info(res, sid):
    username = s.get(f"{base}/users/@me").json()["username"]
    r = s.get(f"{base}/{res}/{sid}").json()
    if res == "guilds":
        print(f"Deleting messages in {r['name']} by {username}")
    elif res == "channels":
        print(f"Deleting messages with {r['recipients'][0]['username']} by {username}")


if __name__ == "__main__":
    main()
