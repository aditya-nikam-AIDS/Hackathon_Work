import argparse
import time

import requests


DEMO_COMPLAINTS = [
    {
        "complaint_text": "I was charged twice for my subscription and need a refund now.",
        "customer_id": "CUST-1001",
        "customer_tier": "premium",
    },
    {
        "complaint_text": "My account was hacked and there is an unauthorized transaction.",
        "customer_id": "CUST-1002",
        "customer_tier": "vip",
    },
    {
        "complaint_text": "The package never arrived even though tracking says delivered.",
        "customer_id": "CUST-1003",
        "customer_tier": "standard",
    },
    {
        "complaint_text": "The mobile app crashes every time I try to login.",
        "customer_id": "CUST-1004",
        "customer_tier": "standard",
    },
    {
        "complaint_text": "The product arrived damaged with a missing part.",
        "customer_id": "CUST-1005",
        "customer_tier": "trial",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo tickets through the API.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--delay", type=float, default=0.2)
    args = parser.parse_args()

    for complaint in DEMO_COMPLAINTS:
        response = requests.post(f"{args.api_url.rstrip('/')}/create-ticket", json=complaint, timeout=10)
        response.raise_for_status()
        ticket = response.json()
        print(f"Created {ticket['id']} -> {ticket['priority']} / {ticket['team']}")
        time.sleep(args.delay)


if __name__ == "__main__":
    main()

