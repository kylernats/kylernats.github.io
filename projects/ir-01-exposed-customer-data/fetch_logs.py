#!/usr/bin/env python3
"""Pull the CloudTrail logs out of S3 and decompress them locally.

This is what you would do at work: get the log files onto your machine, then
query them with whatever you are fastest in. It does not analyse anything.

    python3 fetch_logs.py            -> logs/events.json  (one flat array)
    python3 fetch_logs.py --raw      -> logs/raw/*.json.gz as delivered
"""
import argparse, gzip, io, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "02-ai-security-agent"))
from src import aws_client  # noqa: E402

BUCKET = "meridian-cloudtrail-logs"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", action="store_true", help="also keep the .json.gz files")
    args = ap.parse_args()

    s3 = aws_client.s3()
    out = HERE / "logs"
    out.mkdir(exist_ok=True)

    keys, token = [], None
    while True:
        kw = {"Bucket": BUCKET, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        r = s3.list_objects_v2(**kw)
        keys += [o["Key"] for o in r.get("Contents", [])]
        if not r.get("IsTruncated"):
            break
        token = r.get("NextContinuationToken")

    records = []
    for k in keys:
        body = s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()
        if args.raw:
            p = out / "raw" / Path(k).name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
        records += json.loads(gzip.GzipFile(fileobj=io.BytesIO(body)).read())["Records"]

    records.sort(key=lambda r: r["eventTime"])
    (out / "events.json").write_text(json.dumps(records, indent=2))

    print(f"{len(keys)} log files -> {len(records)} events")
    print(f"written to logs/events.json")
    print("\nTry:")
    print("  jq -r '.[] | \"\\(.eventTime)  \\(.eventName)\"' logs/events.json | head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
