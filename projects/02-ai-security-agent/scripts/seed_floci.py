#!/usr/bin/env python3
"""Seed the local Floci emulator with deliberately misconfigured AWS resources.

Gives the agent something real to find. Everything created here is tagged or
prefixed so `--reset` can remove it again without touching anything else.

    python3 scripts/seed_floci.py           # create the misconfigured estate
    python3 scripts/seed_floci.py --reset   # tear it back down
    python3 scripts/seed_floci.py --show    # list what currently exists

Deliberately includes correctly-configured resources alongside the bad ones. A
detector that flags everything is as useless as one that flags nothing, and the
clean resources are what prove the rules discriminate.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botocore.exceptions import ClientError  # noqa: E402

from src import aws_client  # noqa: E402

log = logging.getLogger("seed")

PREFIX = "agentlab"

BUCKET_PUBLIC = f"{PREFIX}-public-reports"
BUCKET_UNENCRYPTED = f"{PREFIX}-raw-exports"
BUCKET_CLEAN = f"{PREFIX}-locked-archive"

ROLE_INLINE_ADMIN = f"{PREFIX}-ci-deploy-role"
ROLE_ATTACHED_ADMIN = f"{PREFIX}-analytics-role"
ROLE_CLEAN = f"{PREFIX}-readonly-role"
POLICY_ADMIN = f"{PREFIX}-AllowEverything"

QUEUE_OPEN = f"{PREFIX}-ingest-queue"
TABLE_NAME = f"{PREFIX}-findings"
TRAIL_NAME = f"{PREFIX}-trail"
TRAIL_BUCKET = f"{PREFIX}-trail-logs"

ASSUME_EC2 = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
}

ADMIN_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{"Sid": "AllowAll", "Effect": "Allow", "Action": "*", "Resource": "*"}],
}

READONLY_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": [f"arn:aws:s3:::{BUCKET_CLEAN}", f"arn:aws:s3:::{BUCKET_CLEAN}/*"],
    }],
}


def public_bucket_policy(bucket: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
        }],
    }


def open_queue_policy(arn: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AnyoneCanSend",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "sqs:*",
            "Resource": arn,
        }],
    }


def _ignore(exc: ClientError, *codes: str) -> bool:
    return exc.response.get("Error", {}).get("Code") in codes


# --------------------------------------------------------------------- create --
def seed_s3() -> list[str]:
    s3 = aws_client.s3()
    made = []

    for bucket in (BUCKET_PUBLIC, BUCKET_UNENCRYPTED, BUCKET_CLEAN, TRAIL_BUCKET):
        try:
            s3.create_bucket(Bucket=bucket)
            made.append(bucket)
        except ClientError as exc:
            if not _ignore(exc, "BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

    # 1. Publicly readable via bucket policy, no public access block. The classic.
    s3.put_bucket_policy(Bucket=BUCKET_PUBLIC, Policy=json.dumps(public_bucket_policy(BUCKET_PUBLIC)))
    s3.put_object(Bucket=BUCKET_PUBLIC, Key="q3-financials.csv",
                  Body=b"account,spend\nprod,48211.00\n")
    log.info("  %s: public bucket policy, no public access block", BUCKET_PUBLIC)

    # 2. Private, but no encryption and no versioning. Quieter, still a finding.
    s3.put_object(Bucket=BUCKET_UNENCRYPTED, Key="dump.json", Body=b'{"records": 128}')
    log.info("  %s: no default encryption, no versioning", BUCKET_UNENCRYPTED)

    # 3. The control case: locked down properly, so a detector that flags it is wrong.
    s3.put_public_access_block(
        Bucket=BUCKET_CLEAN,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_encryption(
        Bucket=BUCKET_CLEAN,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    s3.put_bucket_versioning(Bucket=BUCKET_CLEAN, VersioningConfiguration={"Status": "Enabled"})
    log.info("  %s: encrypted, versioned, public access blocked (control case)", BUCKET_CLEAN)
    return made


def seed_iam() -> None:
    iam = aws_client.iam()

    for role in (ROLE_INLINE_ADMIN, ROLE_ATTACHED_ADMIN, ROLE_CLEAN):
        try:
            iam.create_role(RoleName=role, AssumeRolePolicyDocument=json.dumps(ASSUME_EC2))
        except ClientError as exc:
            if not _ignore(exc, "EntityAlreadyExists"):
                raise

    # 1. Inline policy granting *:* — invisible unless you enumerate inline policies.
    iam.put_role_policy(RoleName=ROLE_INLINE_ADMIN, PolicyName="inline-admin",
                        PolicyDocument=json.dumps(ADMIN_POLICY))
    log.info("  %s: inline policy with Action:* Resource:*", ROLE_INLINE_ADMIN)

    # 2. Same power, delivered as a managed policy attachment.
    try:
        arn = iam.create_policy(PolicyName=POLICY_ADMIN,
                                PolicyDocument=json.dumps(ADMIN_POLICY))["Policy"]["Arn"]
    except ClientError as exc:
        if not _ignore(exc, "EntityAlreadyExists"):
            raise
        arn = f"arn:aws:iam::{aws_client.account_id()}:policy/{POLICY_ADMIN}"
    iam.attach_role_policy(RoleName=ROLE_ATTACHED_ADMIN, PolicyArn=arn)
    log.info("  %s: managed policy %s attached", ROLE_ATTACHED_ADMIN, POLICY_ADMIN)

    # 3. Control case: scoped to exactly what it needs.
    iam.put_role_policy(RoleName=ROLE_CLEAN, PolicyName="scoped-read",
                        PolicyDocument=json.dumps(READONLY_POLICY))
    log.info("  %s: least-privilege inline policy (control case)", ROLE_CLEAN)


def seed_sqs() -> None:
    sqs = aws_client.sqs()
    url = sqs.create_queue(QueueName=QUEUE_OPEN)["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": json.dumps(open_queue_policy(arn))})
    sqs.send_message(QueueUrl=url, MessageBody=json.dumps(
        {"event": "drift.detected", "resource": BUCKET_PUBLIC, "note": "seeded test event"}))
    log.info("  %s: queue policy allows Principal:* (and one test message)", QUEUE_OPEN)


def seed_dynamodb() -> None:
    ddb = aws_client.dynamodb()
    try:
        ddb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "finding_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "finding_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        log.info("  %s: findings table created", TABLE_NAME)
    except ClientError as exc:
        if not _ignore(exc, "ResourceInUseException"):
            raise


def seed_cloudtrail() -> None:
    ct = aws_client.cloudtrail()
    try:
        ct.create_trail(Name=TRAIL_NAME, S3BucketName=TRAIL_BUCKET, IsMultiRegionTrail=False)
        log.info("  %s: trail created (single-region — itself a finding)", TRAIL_NAME)
    except ClientError as exc:
        if not _ignore(exc, "TrailAlreadyExistsException"):
            raise
    try:
        ct.start_logging(Name=TRAIL_NAME)
    except ClientError:
        pass


# ---------------------------------------------------------------------- reset --
def reset() -> None:
    s3, iam, sqs = aws_client.s3(), aws_client.iam(), aws_client.sqs()

    for bucket in (BUCKET_PUBLIC, BUCKET_UNENCRYPTED, BUCKET_CLEAN, TRAIL_BUCKET):
        try:
            objs = s3.list_objects_v2(Bucket=bucket).get("Contents", [])
            for o in objs:
                s3.delete_object(Bucket=bucket, Key=o["Key"])
            s3.delete_bucket(Bucket=bucket)
            log.info("  removed bucket %s", bucket)
        except ClientError:
            pass

    for role in (ROLE_INLINE_ADMIN, ROLE_ATTACHED_ADMIN, ROLE_CLEAN):
        try:
            for name in iam.list_role_policies(RoleName=role).get("PolicyNames", []):
                iam.delete_role_policy(RoleName=role, PolicyName=name)
            for att in iam.list_attached_role_policies(RoleName=role).get("AttachedPolicies", []):
                iam.detach_role_policy(RoleName=role, PolicyArn=att["PolicyArn"])
            iam.delete_role(RoleName=role)
            log.info("  removed role %s", role)
        except ClientError:
            pass

    try:
        iam.delete_policy(PolicyArn=f"arn:aws:iam::{aws_client.account_id()}:policy/{POLICY_ADMIN}")
        log.info("  removed policy %s", POLICY_ADMIN)
    except ClientError:
        pass

    try:
        sqs.delete_queue(QueueUrl=sqs.get_queue_url(QueueName=QUEUE_OPEN)["QueueUrl"])
        log.info("  removed queue %s", QUEUE_OPEN)
    except ClientError:
        pass

    try:
        aws_client.dynamodb().delete_table(TableName=TABLE_NAME)
        log.info("  removed table %s", TABLE_NAME)
    except ClientError:
        pass

    try:
        aws_client.cloudtrail().delete_trail(Name=TRAIL_NAME)
        log.info("  removed trail %s", TRAIL_NAME)
    except ClientError:
        pass


def show() -> None:
    s3, iam = aws_client.s3(), aws_client.iam()
    print("\nBuckets:")
    for b in s3.list_buckets().get("Buckets", []):
        marks = []
        try:
            s3.get_bucket_policy(Bucket=b["Name"])
            marks.append("has-policy")
        except ClientError:
            pass
        try:
            s3.get_public_access_block(Bucket=b["Name"])
            marks.append("pab")
        except ClientError:
            marks.append("NO-pab")
        print(f"  {b['Name']:<34} {' '.join(marks)}")

    print("\nRoles:")
    for r in iam.list_roles().get("Roles", []):
        inline = iam.list_role_policies(RoleName=r["RoleName"]).get("PolicyNames", [])
        attached = [a["PolicyName"] for a in
                    iam.list_attached_role_policies(RoleName=r["RoleName"]).get("AttachedPolicies", [])]
        print(f"  {r['RoleName']:<34} inline={inline or '-'} attached={attached or '-'}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="remove everything this script creates")
    ap.add_argument("--show", action="store_true", help="list current state and exit")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    info = aws_client.health()
    if not info["reachable"]:
        print(f"Cannot reach the emulator at {info['endpoint']}")
        print(f"  {info.get('error', '')}")
        print("\nIs the Floci container running?  docker ps")
        return 1

    print(f"Floci at {info['endpoint']} (account {info.get('account')})\n")

    if args.show:
        show()
        return 0

    if args.reset:
        print("Removing seeded resources:")
        reset()
        print("\nDone.")
        return 0

    print("Seeding misconfigured resources:")
    seed_s3()
    seed_iam()
    seed_sqs()
    seed_dynamodb()
    seed_cloudtrail()

    print("\nSeeded. Expect the agent to find:")
    print("  - public bucket policy on            ", BUCKET_PUBLIC)
    print("  - no public access block on          ", BUCKET_PUBLIC, "/", BUCKET_UNENCRYPTED)
    print("  - no default encryption on           ", BUCKET_UNENCRYPTED)
    print("  - inline Action:* Resource:* on      ", ROLE_INLINE_ADMIN)
    print("  - managed admin policy attached to   ", ROLE_ATTACHED_ADMIN)
    print("  - queue policy open to everyone on   ", QUEUE_OPEN)
    print("\nAnd to leave these alone:")
    print("  -", BUCKET_CLEAN, "(encrypted, versioned, blocked)")
    print("  -", ROLE_CLEAN, "(least privilege)")
    print("\nNext:  python3 -m src.triage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
