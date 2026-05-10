import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--device-id", default="20845")
    parser.add_argument("--high", type=int, default=120)
    parser.add_argument("--low", type=int, default=90)
    parser.add_argument("--time", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    measure_time = args.time or int(time.time())
    device_id = args.device_id
    base_url = args.base_url.rstrip("/")

    ticket_resp = get_json(
        f"{base_url}/getTicket?{urllib.parse.urlencode({'deviceId': device_id})}"
    )
    ticket = ticket_resp["data"]["ticket"]

    signature = hashlib.md5((ticket + device_id + args.secret).encode("utf-8")).hexdigest()
    token_resp = post_json(
        f"{base_url}/getToken",
        {
            "deviceId": device_id,
            "signature": signature,
            "ticket": ticket,
        },
    )
    token = token_resp["data"]["token"]

    body = {
        "deviceId": device_id,
        "token": token,
        "data": {
            "time": measure_time,
            "high": args.high,
            "low": args.low,
        },
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, separators=(",", ":"))

    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
