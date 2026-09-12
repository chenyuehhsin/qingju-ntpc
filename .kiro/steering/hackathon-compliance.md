---
inclusion: always
---

# Hackathon Compliance Rules

These constraints come from the official hackathon rulebook and apply to all work
in this project. Follow them in every task without needing to be reminded.

## General

- Deploy only in `us-east-1` or `us-west-2`. Default to `us-west-2` for this
  project.
- Never create publicly accessible S3 buckets. Keep S3 Block Public Access on and
  restrict access via bucket policy.
- Never create EC2 security groups that are fully open to the internet
  (e.g. `0.0.0.0/0` on all ports).
- Never create RDS instances or EMR clusters with public access enabled.
- Launch only the instances needed for the current task; avoid idle resources.
- Only use AWS services from the supported services list provided by the
  organizers.
- Do not import or introduce restricted data into the AWS account: personal data,
  regulated/financial/health/payment data, biometric or genetic data, or data on
  race, ethnicity, political/religious/philosophical views, union membership, or
  sexual orientation. Do not introduce malware.

## Secrets

- Never commit credentials (AWS keys, API tokens, DB passwords) to the repo.
- Keep secrets in environment variables or files that are gitignored (`.env`).
- AWS credentials live in `~/.aws/`, outside the repository.

## Kiro / repository

- The `.kiro/` folder and its subfolders (specs, hooks, steering) must stay in the
  repository and must NOT be added to `.gitignore`.

## Amazon Bedrock

- Keep Bedrock requests at or below 1 request per second (RPS/TPS).
- Request access only for models directly needed by this project; do not enable
  all available models.
- Periodically review model access and revoke models no longer in use.

## EC2 / SageMaker

- Use only the instance types allowed by the organizers' supported list.
- Avoid large-scale model training given the limited hackathon time and resources.
