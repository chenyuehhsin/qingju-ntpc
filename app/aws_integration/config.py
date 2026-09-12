from dataclasses import dataclass
import os
import re

TAGS = {"Project": "qingju-ntpc", "Component": "policy-assistant", "Milestone": "4A", "Environment": "hackathon"}


class Blocked(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    region: str = ""
    profile: str = ""
    prefix: str = "qingju-policy-assistant"
    bucket: str = ""
    document_prefix: str = "knowledge/"
    kb_role: str = ""
    gateway_role: str = ""
    lambda_role: str = ""
    lambda_image: str = ""
    kb_id: str = ""
    gateway_id: str = ""

    @classmethod
    def from_env(cls, env=None):
        e = os.environ if env is None else env
        return cls(region=e.get("AWS_REGION") or e.get("AWS_DEFAULT_REGION", ""),
                   profile=e.get("AWS_PROFILE", ""), prefix=e.get("QINGJU_RESOURCE_PREFIX", "qingju-policy-assistant"),
                   bucket=e.get("QINGJU_KB_BUCKET", ""), document_prefix=e.get("QINGJU_KB_PREFIX", "knowledge/"),
                   kb_role=e.get("QINGJU_KB_ROLE_ARN", ""), gateway_role=e.get("QINGJU_GATEWAY_ROLE_ARN", ""),
                   lambda_role=e.get("QINGJU_LAMBDA_ROLE_ARN", ""), lambda_image=e.get("QINGJU_LAMBDA_IMAGE_URI", ""),
                   kb_id=e.get("QINGJU_KB_ID", ""), gateway_id=e.get("QINGJU_GATEWAY_ID", ""))

    def validate(self):
        if not self.region or not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", self.region):
            raise Blocked("AWS_REGION / AWS_DEFAULT_REGION required and must be verified for service availability")
        if not re.fullmatch(r"qingju-policy-assistant(?:-[a-z0-9-]+)?", self.prefix):
            raise Blocked("Use project-scoped resource prefix")
        if not self.bucket or not re.fullmatch(r"qingju-policy-assistant-[a-z0-9-]+", self.bucket):
            raise Blocked("QINGJU_KB_BUCKET must be an explicitly configured project-scoped bucket")
        if not self.document_prefix.endswith("/") or self.document_prefix.startswith("/") or ".." in self.document_prefix:
            raise Blocked("Invalid document prefix")

    def require(self, *fields):
        for name in fields:
            if not getattr(self, name):
                raise Blocked("Missing configuration: " + name)


def verified_session(config):
    """Called only behind explicit --apply / --live; never logs key material."""
    import boto3
    config.validate()
    session = boto3.Session(profile_name=config.profile or None, region_name=config.region)
    if session.get_credentials() is None:
        raise Blocked("AWS_DEPLOYMENT_BLOCKED: no AWS credentials")
    identity = session.client("sts").get_caller_identity()
    return session, {"account": identity["Account"], "arn": identity["Arn"], "region": config.region}
