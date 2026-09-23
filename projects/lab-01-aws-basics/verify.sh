#!/usr/bin/env bash
# Lab 01 — check you did the exercises.
# Run this BEFORE the cleanup step.

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
EP="http://localhost:4566"
A() { aws --endpoint-url "$EP" "$@" 2>/dev/null; }

G=$'\033[32m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
pass=0; total=0

check () { # name, condition-result, detail
  total=$((total+1))
  if [ "$2" = "1" ]; then
    pass=$((pass+1)); printf "  [${G}PASS${N}] %s\n" "$1"
  else
    printf "  [${R}FAIL${N}] %s\n" "$1"
    [ -n "$3" ] && printf "         ${D}%s${N}\n" "$3"
  fi
}

echo
echo "Lab 01 — checks"
echo "---------------"

# 1. emulator reachable
if A s3 ls >/dev/null 2>&1; then r=1; else r=0; fi
check "Emulator is reachable" "$r" "Is the container running? docker ps"

# 2. bucket exists
if A s3api head-bucket --bucket kn-practice >/dev/null 2>&1; then r=1; else r=0; fi
check "Bucket kn-practice exists" "$r" "Step 5: aws ... s3 mb s3://kn-practice"

# 3. file in it
if A s3api head-object --bucket kn-practice --key hello.txt >/dev/null 2>&1; then r=1; else r=0; fi
check "hello.txt is in the bucket" "$r" "Step 6: aws ... s3 cp hello.txt s3://kn-practice/"

# 4. file has content
body=$(A s3 cp s3://kn-practice/hello.txt - 2>/dev/null)
if [ -n "$body" ]; then r=1; else r=0; fi
check "hello.txt has content in it" "$r" "The file uploaded but is empty"

# 5. locked back down
if ! A s3api head-bucket --bucket kn-practice >/dev/null 2>&1; then
  r=0; why="The bucket does not exist yet"
else
  pol=$(A s3api get-bucket-policy --bucket kn-practice --query Policy --output text)
  why="Step 9: you made it public but did not lock it back down"
  if [ -z "$pol" ] || [ "$pol" = "None" ]; then r=1
  elif echo "$pol" | grep -q '"Principal": *"\*"'; then r=0
  else r=1; fi
fi
check "Bucket is no longer public" "$r" "$why"

echo
if [ "$pass" = "$total" ]; then
  printf "  ${G}%s/%s — all good. Move on to the cleanup step.${N}\n\n" "$pass" "$total"
  exit 0
else
  printf "  ${R}%s/%s${N} — see the failing steps above.\n\n" "$pass" "$total"
  exit 1
fi
