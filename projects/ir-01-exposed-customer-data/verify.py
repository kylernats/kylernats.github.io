#!/usr/bin/env python3
"""Lab IR-01 — grade the response.

Two halves, because doing only one of them is the common failure mode:

  CONTAINMENT   did you actually fix the exposure, without breaking the thing
                that is supposed to be public and without destroying evidence
  INVESTIGATION did you work out what happened, from the logs

Fill in answers.json (copy answers.template.json) before running this.

    python3 verify.py
    python3 verify.py --explain    show why each check passed or failed
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "02-ai-security-agent"))

from botocore.exceptions import ClientError  # noqa: E402

from src import aws_client  # noqa: E402

import setup as scenario  # noqa: E402

ANSWERS = HERE / "answers.json"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class Check:
    def __init__(self, name: str, weight: int = 1):
        self.name, self.weight = name, weight
        self.passed: bool | None = None
        self.detail = ""

    def ok(self, detail: str = "") -> "Check":
        self.passed, self.detail = True, detail
        return self

    def fail(self, detail: str) -> "Check":
        self.passed, self.detail = False, detail
        return self


# ------------------------------------------------------------- containment --
def check_containment() -> list[Check]:
    s3 = aws_client.s3()
    out: list[Check] = []

    def policy_is_public(bucket: str) -> bool | None:
        try:
            doc = json.loads(s3.get_bucket_policy(Bucket=bucket)["Policy"])
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchBucketPolicy":
                return False
            return None
        for st in doc.get("Statement", []):
            p = st.get("Principal")
            if st.get("Effect") == "Allow" and (p == "*" or (isinstance(p, dict) and "*" in str(p.values()))):
                return True
        return False

    # 1. the leak is closed
    c = Check("Exposure closed on meridian-customer-exports", 3)
    pub = policy_is_public(scenario.B_EXPORTS)
    out.append(c.fail("bucket policy still grants Principal '*'") if pub
               else c.ok("no public statement in the bucket policy"))

    # 2. backstop in place
    c = Check("Public access block restored on meridian-customer-exports", 2)
    try:
        cfg = s3.get_public_access_block(scenario.B_EXPORTS and
                                         scenario.B_EXPORTS)["PublicAccessBlockConfiguration"] \
            if False else s3.get_public_access_block(
                Bucket=scenario.B_EXPORTS)["PublicAccessBlockConfiguration"]
        missing = [k for k, v in {
            "BlockPublicAcls": cfg.get("BlockPublicAcls"),
            "IgnorePublicAcls": cfg.get("IgnorePublicAcls"),
            "BlockPublicPolicy": cfg.get("BlockPublicPolicy"),
            "RestrictPublicBuckets": cfg.get("RestrictPublicBuckets"),
        }.items() if not v]
        out.append(c.ok("all four settings enabled") if not missing
                   else c.fail(f"not enabled: {', '.join(missing)}"))
    except ClientError:
        out.append(c.fail("no public access block configured"))

    # 3. did NOT break the website
    c = Check("meridian-web-assets left public (it serves the website)", 3)
    pub = policy_is_public(scenario.B_WEB)
    if pub:
        out.append(c.ok("still publicly readable, as intended"))
    else:
        out.append(c.fail("this bucket was public on purpose — removing it takes the "
                          "company website down. Over-remediation is an outage."))

    # 4. evidence preserved
    c = Check("CloudTrail logs preserved", 2)
    try:
        n = s3.list_objects_v2(Bucket=scenario.B_TRAIL).get("KeyCount", 0)
        out.append(c.ok(f"{n} log files intact") if n >= 40
                   else c.fail(f"only {n} log files remain — evidence was destroyed"))
    except ClientError:
        out.append(c.fail("trail bucket missing entirely"))

    # 5. data not deleted
    c = Check("Exported data not deleted", 1)
    try:
        n = s3.list_objects_v2(Bucket=scenario.B_EXPORTS).get("KeyCount", 0)
        out.append(c.ok(f"{n} objects still present") if n >= 4
                   else c.fail(f"{n} objects left — deleting the data is not containment, "
                               "and it destroys what you need for breach notification"))
    except ClientError:
        out.append(c.fail("bucket missing"))

    # 6. internal bucket untouched
    c = Check("meridian-internal-docs still locked down", 1)
    pub = policy_is_public(scenario.B_INTERNAL)
    out.append(c.ok("unchanged") if pub is False else c.fail("this bucket became public"))

    return out


# ---------------------------------------------------------- investigation --
def load_records() -> list[dict]:
    s3 = aws_client.s3()
    recs: list[dict] = []
    token = None
    while True:
        kw: dict = {"Bucket": scenario.B_TRAIL, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for o in resp.get("Contents", []):
            body = s3.get_object(Bucket=scenario.B_TRAIL, Key=o["Key"])["Body"].read()
            recs += json.loads(gzip.GzipFile(fileobj=io.BytesIO(body)).read())["Records"]
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return recs


def ground_truth() -> dict:
    recs = load_records()
    change = next(e for e in recs if e["eventName"] == "PutBucketPolicy"
                  and e["requestParameters"].get("bucketName") == scenario.B_EXPORTS)
    anon = [e for e in recs if e["eventName"] == "GetObject"
            and e["userIdentity"].get("type") == "AWSAccount"
            and e["requestParameters"].get("bucketName") == scenario.B_EXPORTS
            and "errorCode" not in e]
    return {
        "date_made_public": change["eventTime"][:10],
        "who_made_it_public": change["userIdentity"]["userName"],
        "source_ip_of_change": change["sourceIPAddress"],
        "external_ips_that_downloaded": sorted({e["sourceIPAddress"] for e in anon}),
        "objects_downloaded": sorted({e["requestParameters"]["key"] for e in anon}),
        "successful_anonymous_downloads": len(anon),
    }


def check_investigation(explain: bool) -> list[Check]:
    if not ANSWERS.is_file():
        return [Check("answers.json submitted", 6).fail(
            "not found — copy answers.template.json to answers.json and fill it in")]

    try:
        given = json.loads(ANSWERS.read_text())
    except json.JSONDecodeError as exc:
        return [Check("answers.json is valid JSON", 6).fail(str(exc))]

    truth = ground_truth()
    out: list[Check] = []

    def norm(v):
        return str(v).strip().lower()

    # date
    c = Check("Date the bucket was made public", 2)
    want = truth["date_made_public"]
    got = norm(given.get("date_made_public", ""))
    out.append(c.ok(want) if got == want.lower()
               else c.fail(f"got {got or '(blank)'}" + (f", expected {want}" if explain else "")))

    # who
    c = Check("Identity that made the change", 2)
    want = truth["who_made_it_public"]
    got = norm(given.get("who_made_it_public", ""))
    out.append(c.ok(want) if want.lower() in got or got in want.lower() and got
               else c.fail(f"got {got or '(blank)'}" + (f", expected {want}" if explain else "")))

    # source ip
    c = Check("Source IP of the change", 1)
    want = truth["source_ip_of_change"]
    got = norm(given.get("source_ip_of_change", ""))
    out.append(c.ok(want) if got == want
               else c.fail(f"got {got or '(blank)'}" + (f", expected {want}" if explain else "")))

    # external ips
    c = Check("External IPs that downloaded data", 2)
    want = set(truth["external_ips_that_downloaded"])
    got = {norm(x) for x in given.get("external_ips_that_downloaded", []) if str(x).strip()}
    if got == want:
        out.append(c.ok(f"{len(want)} addresses, all correct"))
    else:
        miss, extra = want - got, got - want
        bits = []
        if miss:
            bits.append(f"missed {len(miss)}")
        if extra:
            bits.append(f"{len(extra)} not in the logs")
        out.append(c.fail("; ".join(bits) + (f" — expected {sorted(want)}" if explain else "")))

    # objects taken
    c = Check("Objects actually downloaded by outsiders", 2)
    want = set(truth["objects_downloaded"])
    got = {norm(x) for x in given.get("objects_downloaded", []) if str(x).strip()}
    if got == want:
        out.append(c.ok(f"{len(want)} objects, all correct"))
    else:
        out.append(c.fail(f"got {len(got)}, expected {len(want)}"
                          + (f" — {sorted(want)}" if explain else "")))

    # count
    c = Check("Number of successful anonymous downloads", 1)
    want = truth["successful_anonymous_downloads"]
    try:
        got_n = int(given.get("successful_anonymous_downloads", -1))
    except (TypeError, ValueError):
        got_n = -1
    out.append(c.ok(str(want)) if got_n == want
               else c.fail(f"got {got_n if got_n >= 0 else '(blank)'}"
                           + (f", expected {want}" if explain else "")))

    # judgement call
    c = Check("Correct call on meridian-web-assets", 2)
    got = norm(given.get("web_assets_decision", ""))
    if got.startswith("leave") or "intentional" in got or "keep" in got:
        out.append(c.ok("identified as intentionally public"))
    else:
        out.append(c.fail("expected 'leave' — that bucket serves the public website"
                          if explain else f"got {got or '(blank)'}"))

    return out


# ------------------------------------------------------------------ report --
def report(sections: dict[str, list[Check]]) -> int:
    total = earned = 0
    for title, checks in sections.items():
        print(f"\n{title}")
        print("-" * len(title))
        for c in checks:
            total += c.weight
            mark = f"{GREEN}PASS{RESET}" if c.passed else f"{RED}FAIL{RESET}"
            if c.passed:
                earned += c.weight
            print(f"  [{mark}] {c.name}")
            if c.detail:
                print(f"         {DIM}{c.detail}{RESET}")

    pct = round(earned / total * 100) if total else 0
    colour = GREEN if pct >= 90 else (YELLOW if pct >= 60 else RED)
    print(f"\n{'=' * 52}")
    print(f"  SCORE: {colour}{earned}/{total}  ({pct}%){RESET}")
    if pct == 100:
        print("  Complete. Capture your screenshots and write the summary.")
    elif pct >= 60:
        print("  Close. Re-run with --explain to see what is off.")
    else:
        print("  Keep going. Nothing is graded on time.")
    print("=" * 52)
    return 0 if pct == 100 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--explain", action="store_true", help="reveal expected values on failures")
    ap.add_argument("--truth", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    h = aws_client.health()
    if not h["reachable"]:
        print(f"Floci unreachable at {h['endpoint']}.")
        return 1

    if args.truth:
        print(json.dumps(ground_truth(), indent=2))
        return 0

    return report({
        "CONTAINMENT — did you fix it, and only it": check_containment(),
        "INVESTIGATION — did you work out what happened": check_investigation(args.explain),
    })


if __name__ == "__main__":
    raise SystemExit(main())
