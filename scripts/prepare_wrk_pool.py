import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def cmd_tickets(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    ensure_parent(out_path)
    base_url = args.base_url.rstrip("/")

    with out_path.open("w", encoding="utf-8") as f:
        for idx in range(args.count):
            resp = get_json(
                f"{base_url}/getTicket?{urllib.parse.urlencode({'deviceId': args.device_id})}"
            )
            if resp.get("code") != 200:
                raise SystemExit(f"getTicket failed at {idx}: {resp}")
            f.write(resp["data"]["ticket"] + "\n")

    print(out_path)
    return 0


def cmd_gettoken_bodies(args: argparse.Namespace) -> int:
    tickets_path = Path(args.tickets)
    out_path = Path(args.out)
    ensure_parent(out_path)

    with tickets_path.open("r", encoding="utf-8") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            ticket = line.strip()
            if not ticket:
                continue
            signature = hashlib.md5(
                (ticket + args.device_id + args.secret).encode("utf-8")
            ).hexdigest()
            body = {
                "deviceId": args.device_id,
                "signature": signature,
                "ticket": ticket,
            }
            fout.write(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(out_path)
    return 0


def cmd_tokens(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    ensure_parent(out_path)
    base_url = args.base_url.rstrip("/")

    with out_path.open("w", encoding="utf-8") as f:
        for idx in range(args.count):
            ticket_resp = get_json(
                f"{base_url}/getTicket?{urllib.parse.urlencode({'deviceId': args.device_id})}"
            )
            if ticket_resp.get("code") != 200:
                raise SystemExit(f"getTicket failed at {idx}: {ticket_resp}")

            ticket = ticket_resp["data"]["ticket"]
            signature = hashlib.md5(
                (ticket + args.device_id + args.secret).encode("utf-8")
            ).hexdigest()
            token_resp = post_json(
                f"{base_url}/getToken",
                {
                    "deviceId": args.device_id,
                    "signature": signature,
                    "ticket": ticket,
                },
            )
            if token_resp.get("code") != 200:
                raise SystemExit(f"getToken failed at {idx}: {token_resp}")

            f.write(token_resp["data"]["token"] + "\n")

    print(out_path)
    return 0


def cmd_upload_bodies(args: argparse.Namespace) -> int:
    tokens_path = Path(args.tokens)
    out_path = Path(args.out)
    ensure_parent(out_path)
    base_time = args.base_time or int(time.time())

    with tokens_path.open("r", encoding="utf-8") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        idx = 0
        for line in fin:
            token = line.strip()
            if not token:
                continue
            body = {
                "deviceId": args.device_id,
                "token": token,
                "data": {
                    "time": base_time + idx,
                    "high": args.high,
                    "low": args.low,
                },
            }
            fout.write(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n")
            idx += 1

    print(out_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    tickets = subparsers.add_parser("tickets")
    tickets.add_argument("--base-url", required=True)
    tickets.add_argument("--device-id", required=True)
    tickets.add_argument("--count", type=int, required=True)
    tickets.add_argument("--out", required=True)
    tickets.set_defaults(func=cmd_tickets)

    gettoken_bodies = subparsers.add_parser("gettoken-bodies")
    gettoken_bodies.add_argument("--device-id", required=True)
    gettoken_bodies.add_argument("--secret", required=True)
    gettoken_bodies.add_argument("--tickets", required=True)
    gettoken_bodies.add_argument("--out", required=True)
    gettoken_bodies.set_defaults(func=cmd_gettoken_bodies)

    tokens = subparsers.add_parser("tokens")
    tokens.add_argument("--base-url", required=True)
    tokens.add_argument("--device-id", required=True)
    tokens.add_argument("--secret", required=True)
    tokens.add_argument("--count", type=int, required=True)
    tokens.add_argument("--out", required=True)
    tokens.set_defaults(func=cmd_tokens)

    upload_bodies = subparsers.add_parser("upload-bodies")
    upload_bodies.add_argument("--device-id", required=True)
    upload_bodies.add_argument("--tokens", required=True)
    upload_bodies.add_argument("--high", type=int, default=120)
    upload_bodies.add_argument("--low", type=int, default=80)
    upload_bodies.add_argument("--base-time", type=int, default=0)
    upload_bodies.add_argument("--out", required=True)
    upload_bodies.set_defaults(func=cmd_upload_bodies)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
