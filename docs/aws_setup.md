# AWS S3 setup (optional, about 30-45 minutes)

The pipeline works without AWS (raw files stay in `data/archive/`). Turn S3 on when the core pipeline already works.

Storage cost is very small (24 monthly ZIPs are well under 1 GB), but **set the budget alert anyway** so nothing surprises you.

## 1. Account safety first
1. Create or sign in to your AWS account. Turn on **MFA** for the root user.
2. **Billing → Budgets → Create budget → Zero spend budget** (or a $5 monthly budget) with your email. You get an email if anything costs money.

## 2. Bucket
1. **S3 → Create bucket**. Name: something unique like `flight-reliability-raw-<yourname>`. Region: `us-west-2` (or your nearest; use the same value for `AWS_REGION`).
2. Keep **Block all public access** ON.
3. **Bucket Versioning: Enable** (an overwritten file keeps its old version).
4. Default encryption: SSE-S3 (the default).

## 3. A limited user for the pipeline (least privilege)
1. **IAM → Users → Create user** `flight-pipeline` (no console access).
2. Attach an inline policy (replace the bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::flight-reliability-raw-yourname"
    },
    {
      "Sid": "ReadWriteRawFiles",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::flight-reliability-raw-yourname/raw/*"
    }
  ]
}
```

No delete permission: the pipeline can add and read raw files but never destroy them.

3. **Security credentials → Create access key** (use case: "Application running outside AWS"). Copy both values once.

## 4. Connect it
- **Your Mac:** in `.env` set `S3_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
- **GitHub:** repo → Settings → Secrets and variables → Actions
  - Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - Variables: `S3_BUCKET`, `AWS_REGION`

## 5. Check it
```bash
python -m pipeline.ingest --months-back 1
```
The log should say `raw archive: S3 bucket …` and `archived to s3://…`. In the S3 console you should see `raw/bts_ontime/year=YYYY/month=MM/…zip`, with a `sha256` value under the object's metadata.

## 6. Never leak keys
- `.env` is in `.gitignore`. Before every commit run `git status` and make sure `.env` is not listed.
- If a key is ever pushed to GitHub: **deactivate it in IAM immediately**, create a new one.
