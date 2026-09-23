#!/usr/bin/env python3
"""Lab IR-01 — seed the incident.

Builds a small company estate in Floci and puts it in the state it would be in
on the morning the exposure is reported. Nothing here is a hint: the evidence
needed to answer the questions is all in the CloudTrail logs delivered to S3,
exactly as real CloudTrail delivers them.

    python3 setup.py           build the scenario
    python3 setup.py --reset   tear it down
    python3 setup.py --status  show what exists right now
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02-ai-security-agent"))

from botocore.exceptions import ClientError  # noqa: E402

from src import aws_client  # noqa: E402

ACCOUNT = "000000000000"
REGION = "us-east-1"

# --- the estate -------------------------------------------------------------
B_EXPORTS = "meridian-customer-exports"   # the leak
B_INTERNAL = "meridian-internal-docs"     # private, fine
B_WEB = "meridian-web-assets"             # public ON PURPOSE - the trap
B_TRAIL = "meridian-cloudtrail-logs"      # where the evidence lives

ROLE_CI = "meridian-ci-deploy"
ROLE_ANALYST = "meridian-analyst"

ALL_BUCKETS = [B_EXPORTS, B_INTERNAL, B_WEB, B_TRAIL]

# --- ground truth, used by verify.py ----------------------------------------
# The change was made 3 days ago at 02:47 UTC by an automation identity.
BREACH_AT = (datetime.now(timezone.utc) - timedelta(days=3)).replace(
    hour=2, minute=47, second=13, microsecond=0)
BREACH_ACTOR = "svc-ci-deploy"
BREACH_ACTOR_IP = "198.51.100.23"

# Objects actually pulled by outsiders, and the addresses that pulled them.
EXTERNAL_IPS = ["45.155.205.211", "185.220.101.47", "91.219.236.18"]
STOLEN_KEYS = [
    "exports/2026-09/shipments-customers.csv",
    "exports/2026-09/billing-contacts.csv",
    "exports/2026-08/shipments-customers.csv",
]

OFFICE_IPS = ["203.0.113.11", "203.0.113.12"]


def public_policy(bucket: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowPublicRead",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
        }],
    }


# --- CloudTrail record construction -----------------------------------------
def _record(*, when: datetime, name: str, source_ip: str, user: str,
            user_type: str = "AssumedRole", params=None, resources=None,
            read_only: bool, error: str | None = None) -> dict:
    rec = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": user_type,
            "principalId": f"AIDA{uuid.uuid4().hex[:16].upper()}",
            "arn": (f"arn:aws:sts::{ACCOUNT}:assumed-role/{ROLE_CI}/{user}"
                    if user_type == "AssumedRole" else
                    f"arn:aws:iam::{ACCOUNT}:user/{user}"),
            "accountId": ACCOUNT,
            "userName": user,
        },
        "eventTime": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "eventSource": "s3.amazonaws.com",
        "eventName": name,
        "awsRegion": REGION,
        "sourceIPAddress": source_ip,
        "userAgent": "[aws-cli/2.15.0 Python/3.11]" if user_type == "AssumedRole" else "[S3Console]",
        "requestParameters": params or {},
        "responseElements": None,
        "requestID": uuid.uuid4().hex[:16].upper(),
        "eventID": str(uuid.uuid4()),
        "readOnly": read_only,
        "eventType": "AwsApiCall",
        "managementEvent": not read_only,
        "recipientAccountId": ACCOUNT,
    }
    if resources:
        rec["resources"] = resources
    if error:
        rec["errorCode"] = error
    return rec


def build_trail_records() -> list[dict]:
    """The full story, in the order it happened."""
    recs: list[dict] = []
    anon = {"type": "AWSAccount", "accountId": "anonymous", "principalId": "anonymous"}

    # --- background noise: normal internal activity over the last week -------
    for day in range(7, 0, -1):
        base = datetime.now(timezone.utc) - timedelta(days=day)
        for _ in range(random.randint(4, 9)):
            t = base.replace(hour=random.randint(8, 18), minute=random.randint(0, 59),
                             second=random.randint(0, 59), microsecond=0)
            recs.append(_record(
                when=t, name=random.choice(["GetObject", "PutObject", "ListBucket"]),
                source_ip=random.choice(OFFICE_IPS), user="analyst.jrivera",
                user_type="IAMUser", read_only=True,
                params={"bucketName": random.choice([B_INTERNAL, B_EXPORTS])}))

    # --- the change that caused it ------------------------------------------
    recs.append(_record(
        when=BREACH_AT, name="PutBucketPolicy",
        source_ip=BREACH_ACTOR_IP, user=BREACH_ACTOR, read_only=False,
        params={"bucketName": B_EXPORTS,
                "bucketPolicy": public_policy(B_EXPORTS)},
        resources=[{"type": "AWS::S3::Bucket", "ARN": f"arn:aws:s3:::{B_EXPORTS}"}]))

    # Same actor also removed the public access block minutes earlier - without
    # that, the policy would have been blocked and none of this would matter.
    recs.insert(-1, _record(
        when=BREACH_AT - timedelta(minutes=4), name="DeletePublicAccessBlock",
        source_ip=BREACH_ACTOR_IP, user=BREACH_ACTOR, read_only=False,
        params={"bucketName": B_EXPORTS},
        resources=[{"type": "AWS::S3::Bucket", "ARN": f"arn:aws:s3:::{B_EXPORTS}"}]))

    # --- discovery and exfiltration by outsiders ----------------------------
    # A scanner finds it about 9 hours later, then pulls escalate.
    first_hit = BREACH_AT + timedelta(hours=9, minutes=12)
    recs.append(_record(
        when=first_hit, name="ListBucket", source_ip=EXTERNAL_IPS[0],
        user="anonymous", user_type="AWSAccount", read_only=True,
        params={"bucketName": B_EXPORTS}))
    recs[-1]["userIdentity"] = anon

    t = first_hit
    for i in range(14):
        t += timedelta(minutes=random.randint(25, 210))
        if t > datetime.now(timezone.utc):
            break
        r = _record(when=t, name="GetObject",
                    source_ip=EXTERNAL_IPS[i % len(EXTERNAL_IPS)],
                    user="anonymous", user_type="AWSAccount", read_only=True,
                    params={"bucketName": B_EXPORTS,
                            "key": STOLEN_KEYS[i % len(STOLEN_KEYS)]})
        r["userIdentity"] = anon
        recs.append(r)

    # --- decoys: denied attempts against the buckets that stayed locked -----
    for i in range(4):
        t = BREACH_AT + timedelta(hours=12 + i * 7)
        r = _record(when=t, name="GetObject", source_ip=EXTERNAL_IPS[i % 3],
                    user="anonymous", user_type="AWSAccount", read_only=True,
                    params={"bucketName": B_INTERNAL, "key": "hr/salaries.xlsx"},
                    error="AccessDenied")
        r["userIdentity"] = anon
        recs.append(r)

    # Legitimate public traffic to the website bucket, so "public" alone is not
    # the signal. The analyst has to tell intended public from accidental public.
    for i in range(10):
        t = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 140))
        r = _record(when=t, name="GetObject", source_ip=f"104.28.{random.randint(1,250)}.{random.randint(1,250)}",
                    user="anonymous", user_type="AWSAccount", read_only=True,
                    params={"bucketName": B_WEB, "key": "css/site.css"})
        r["userIdentity"] = anon
        recs.append(r)

    recs.sort(key=lambda r: r["eventTime"])
    return recs


def deliver_logs(records: list[dict]) -> int:
    """Write records into the trail bucket the way CloudTrail delivers them:
    gzipped JSON, one file per hour, under AWSLogs/<account>/CloudTrail/<region>/."""
    s3 = aws_client.s3()
    buckets: dict[str, list[dict]] = {}
    for r in records:
        hour = r["eventTime"][:13]
        buckets.setdefault(hour, []).append(r)

    written = 0
    for hour, recs in sorted(buckets.items()):
        dt = datetime.strptime(hour, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
        key = (f"AWSLogs/{ACCOUNT}/CloudTrail/{REGION}/"
               f"{dt:%Y/%m/%d}/{ACCOUNT}_CloudTrail_{REGION}_{dt:%Y%m%dT%H%M}Z_"
               f"{uuid.uuid4().hex[:16]}.json.gz")
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(json.dumps({"Records": recs}).encode())
        s3.put_object(Bucket=B_TRAIL, Key=key, Body=buf.getvalue())
        written += 1
    return written


# --- build ------------------------------------------------------------------
def build() -> None:
    s3, iam = aws_client.s3(), aws_client.iam()

    for b in ALL_BUCKETS:
        try:
            s3.create_bucket(Bucket=b)
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in (
                    "BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

    lock = {"BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True}

    # The leaked bucket: public policy, public access block removed.
    s3.put_bucket_policy(Bucket=B_EXPORTS, Policy=json.dumps(public_policy(B_EXPORTS)))
    for key, body in [
        ("exports/2026-09/shipments-customers.csv",
         b"order_id,customer_name,email,phone,address,value_usd\n"
         b"SHP-88211,Dana Whitfield,d.whitfield@example.com,+1-303-555-0142,"
         b"884 Cedar Ave Denver CO,18420.00\n"
         b"SHP-88212,Marcus Oyelaran,m.oyelaran@example.net,+1-720-555-0198,"
         b"12 Juniper Ct Aurora CO,2290.50\n"),
        ("exports/2026-09/billing-contacts.csv",
         b"account,contact,email,card_last4\n"
         b"ACME-4471,R. Castellanos,ap@acme-supply.example,4412\n"),
        ("exports/2026-08/shipments-customers.csv",
         b"order_id,customer_name,email,phone,address,value_usd\n"
         b"SHP-81002,Priya Raghunathan,p.raghu@example.org,+1-415-555-0110,"
         b"77 Alder St San Jose CA,9105.75\n"),
        ("exports/README.txt", b"Nightly export of customer shipment records. Internal only.\n"),
    ]:
        s3.put_object(Bucket=B_EXPORTS, Key=key, Body=body)

    # Internal bucket: correctly locked down.
    s3.put_public_access_block(Bucket=B_INTERNAL, PublicAccessBlockConfiguration=lock)
    s3.put_object(Bucket=B_INTERNAL, Key="hr/salaries.xlsx", Body=b"(binary)")
    s3.put_object(Bucket=B_INTERNAL, Key="legal/msa-2026.pdf", Body=b"(binary)")

    # Website assets: public ON PURPOSE. Breaking this breaks the company site.
    s3.put_bucket_policy(Bucket=B_WEB, Policy=json.dumps(public_policy(B_WEB)))
    s3.put_object(Bucket=B_WEB, Key="css/site.css", Body=b"body{font-family:sans-serif}")
    s3.put_object(Bucket=B_WEB, Key="index.html",
                  Body=b"<h1>Meridian Freight</h1><p>Track your shipment.</p>")
    s3.put_object(Bucket=B_WEB, Key="PURPOSE.txt",
                  Body=b"Public static assets for www.meridianfreight.example. "
                       b"This bucket is intentionally world-readable.\n")

    # Trail bucket: locked, holds the evidence.
    s3.put_public_access_block(Bucket=B_TRAIL, PublicAccessBlockConfiguration=lock)

    # Roles
    assume = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"}]}
    for role, doc in [
        (ROLE_CI, {"Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Action": ["s3:*"], "Resource": "*"}]}),
        (ROLE_ANALYST, {"Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{B_INTERNAL}", f"arn:aws:s3:::{B_INTERNAL}/*"]}]}),
    ]:
        try:
            iam.create_role(RoleName=role, AssumeRolePolicyDocument=json.dumps(assume))
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "EntityAlreadyExists":
                raise
        iam.put_role_policy(RoleName=role, PolicyName="inline",
                            PolicyDocument=json.dumps(doc))

    n = deliver_logs(build_trail_records())

    print("Scenario built.\n")
    print(f"  {B_EXPORTS:<30} public, contains customer PII")
    print(f"  {B_INTERNAL:<30} locked down")
    print(f"  {B_WEB:<30} public (intentionally - it serves the website)")
    print(f"  {B_TRAIL:<30} {n} CloudTrail log files delivered")
    print(f"\n  roles: {ROLE_CI}, {ROLE_ANALYST}")
    print("\nOpen the lab brief and start at step 1.")


def reset() -> None:
    s3, iam = aws_client.s3(), aws_client.iam()
    for b in ALL_BUCKETS:
        try:
            token = None
            while True:
                kw = {"Bucket": b, "MaxKeys": 1000}
                if token:
                    kw["ContinuationToken"] = token
                resp = s3.list_objects_v2(**kw)
                for o in resp.get("Contents", []):
                    s3.delete_object(Bucket=b, Key=o["Key"])
                if not resp.get("IsTruncated"):
                    break
                token = resp.get("NextContinuationToken")
            s3.delete_bucket(Bucket=b)
            print(f"  removed {b}")
        except ClientError:
            pass
    for role in (ROLE_CI, ROLE_ANALYST):
        try:
            for p in iam.list_role_policies(RoleName=role).get("PolicyNames", []):
                iam.delete_role_policy(RoleName=role, PolicyName=p)
            iam.delete_role(RoleName=role)
            print(f"  removed {role}")
        except ClientError:
            pass


def status() -> None:
    s3 = aws_client.s3()
    print(f"\n{'BUCKET':<32} {'POLICY':<10} {'PUBLIC-BLOCK':<14} OBJECTS")
    for b in ALL_BUCKETS:
        try:
            s3.head_bucket(Bucket=b)
        except ClientError:
            print(f"{b:<32} (does not exist)")
            continue
        try:
            doc = json.loads(s3.get_bucket_policy(Bucket=b)["Policy"])
            pub = any(s.get("Principal") == "*" for s in doc.get("Statement", []))
            pol = "PUBLIC" if pub else "private"
        except ClientError:
            pol = "none"
        try:
            cfg = s3.get_public_access_block(Bucket=b)["PublicAccessBlockConfiguration"]
            blk = "all on" if all(cfg.values()) else "partial"
        except ClientError:
            blk = "NONE"
        n = s3.list_objects_v2(Bucket=b).get("KeyCount", 0)
        print(f"{b:<32} {pol:<10} {blk:<14} {n}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    h = aws_client.health()
    if not h["reachable"]:
        print(f"Floci unreachable at {h['endpoint']}. Is the container running?")
        return 1

    if args.status:
        status()
    elif args.reset:
        print("Removing scenario:")
        reset()
    else:
        random.seed(20260923)   # same story every rebuild
        build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
