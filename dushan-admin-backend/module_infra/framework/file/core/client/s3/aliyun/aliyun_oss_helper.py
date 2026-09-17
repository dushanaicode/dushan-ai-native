from __future__ import annotations

import asyncio
import re

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig


class AliyunOssHelper:
    """阿里云OSS辅助类，提供OSS专用的客户端初始化和上传操作"""

    @staticmethod
    def check_and_fix_config(config: S3FileClientConfig) -> tuple[S3FileClientConfig, bool]:
        modified = False
        if "." in config.bucket:
            if ".oss-" in config.bucket.lower():
                original_bucket = config.bucket
                parts = original_bucket.split(".")
                config.bucket = parts[0]
                modified = True
        if not config.region and "oss-" in config.endpoint:
            endpoint_parts = config.endpoint.split(".")
            if len(endpoint_parts) >= 2 and endpoint_parts[0].startswith("oss-"):
                region_part = endpoint_parts[0]
                if region_part.startswith("oss-"):
                    region = region_part[4:]
                    config.region = region
                    modified = True
        return (config, modified)

    @staticmethod
    def build_domain(config: S3FileClientConfig) -> str:
        """根据配置构建阿里云OSS的访问域名"""
        endpoint = config.endpoint
        bucket = config.bucket
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return f"{endpoint.rstrip('/')}/{bucket}"
        elif endpoint.startswith("oss-"):
            return f"https://{bucket}.{endpoint}"
        else:
            return f"https://{bucket}.{endpoint}"

    @staticmethod
    def build_endpoint(endpoint: str) -> str:
        """确保endpoint格式正确并添加协议前缀"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        if not endpoint.startswith("oss-"):
            pass
        return f"https://{endpoint}"

    @staticmethod
    def create_client(config: S3FileClientConfig) -> boto3.client:
        """创建阿里云OSS客户端"""
        endpoint = AliyunOssHelper.build_endpoint(config.endpoint)
        region = config.region or "cn-hangzhou"
        valid_bucket_pattern = re.compile("^[a-z0-9][a-z0-9\\-]{1,61}[a-z0-9]$")
        if not valid_bucket_pattern.match(config.bucket):
            pass
        s3_config = BotoConfig(
            s3={
                "addressing_style": "virtual",
                "payload_signing_enabled": False,
                "chunked_encoding": False,
                "use_accelerate_endpoint": False,
                "use_dualstack_endpoint": False,
            },
            signature_version="s3",
            retries={"max_attempts": 3, "mode": "standard"},
        )
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.access_secret,
            region_name=region,
            config=s3_config,
        )
        return client

    @staticmethod
    async def upload_file(
        client: boto3.client,
        bucket: str,
        key: str,
        content: bytes,
        file_type: str = "application/octet-stream",
    ) -> None:
        """上传文件到阿里云OSS，处理特殊错误情况"""
        try:
            await asyncio.to_thread(
                client.put_object, Bucket=bucket, Key=key, Body=content, ContentType=file_type
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", "")
            if "chunked" in error_message.lower() or "sha256" in error_message.lower():
                error_details = f"阿里云OSS不完全兼容AWS S3标准。错误: {error_message}\n建议使用阿里云官方SDK进行上传，或尝试以下解决方案:\n1. 确保boto3版本较新 (pip install boto3 --upgrade)\n2. 文件大小为 {len(content)} 字节，考虑对大文件使用分段上传\n3. 检查endpoint格式 (当前: {client.meta.endpoint_url})"
                raise IOError(error_details) from e
            elif error_code == "InvalidBucketName":
                raise IOError(
                    f"S3 Bucket名称无效: {error_message} - 检查名称格式是否符合规范"
                ) from e
            else:
                raise
