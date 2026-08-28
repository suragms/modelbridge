#!/usr/bin/env python3
"""Minimal ModelBridge chat example.

Setup:
  export MODELBRIDGE_URL=http://localhost:8000
  export MODELBRIDGE_API_KEY=mb_your_key

Run:
  pip install -e ../../packages/python-sdk
  python main.py
"""

import os

from modelbridge import ModelBridge


def main():
    client = ModelBridge(
        base_url=os.environ.get("MODELBRIDGE_URL", "http://localhost:8000"),
        api_key=os.environ["MODELBRIDGE_API_KEY"],
    )
    response = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": "Explain ModelBridge in one sentence."}],
    )
    print(response["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
