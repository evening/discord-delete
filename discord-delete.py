import configparser
import requests
import time

config = configparser.ConfigParser()
config.read("account.ini")
s = requests.Session()
s.headers, base = (
    {"Authorization": config["Account"]["auth_key"]},
    "https://discordapp.com/api/v6",
)

# def convert user ID to channel(DM) ID
# for channel in s.get(f"{base}/users/@me/channels", params=params).json():
#     if channel["type"] == 1 and channel["recipients"][0]["id"] == "#########":
#         return print(channel["id"])
#     for c, msg in enumerate(messages("channels", resource_id, user_id, params), 1):


def main():
    user_id = config["Account"]["user_id"]
    resource_id = config["Account"]["resource_id"]
    params = {k: v for k, v in config["Params"].items() if v}
    params.update({"author_id": user_id})
    info("guilds", resource_id, user_id)  # guilds, channels
    for c, msg in enumerate(messages("guilds", resource_id, user_id, params), 1):
        # https://discord.com/developers/docs/reference#snowflakes
        d = time.gmtime(((int(msg["id"]) >> 22) + 1_420_070_400_000) / 1000)
        print(c, f"{d.tm_mon}/{d.tm_mday}/{d.tm_year}", repr(msg["content"]))
        delete(msg)


def messages(res, rid, uid, params):
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
            yield from messages(res, rid, uid, params)
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


def info(res, sid, uid):
    r = s.get(f"{base}/{res}/{sid}")
    if r.status_code != 200:
        sys.exit(r.json())
    resource_name = r.json().get("name")
    r = s.get(f"{base}/users/{uid}")
    if r.status_code != 200:
        sys.exit(r.json())
    username = r.json()["username"]
    print(f"Deleting messages in {resource_name} by {username}")


if __name__ == "__main__":
    main()
