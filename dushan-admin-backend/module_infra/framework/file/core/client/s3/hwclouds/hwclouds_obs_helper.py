from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import ClientError

from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig


class HuaweiObsHelper:
    """华为云OBS辅助类，提供OBS专用的客户端初始化和上传操作"""

    @staticmethod
    def extract_region_from_endpoint(endpoint: str) -> str:
        """从endpoint中提取region"""
        if "obs.cn-" in endpoint:
            parts = endpoint.split(".")
            if len(parts) >= 3 and parts[0] == "obs":
                region = parts[1]
                return region
        return "cn-north-1"

    @staticmethod
    def build_domain(config: S3FileClientConfig) -> str:
        """根据配置构建华为云OBS的访问域名"""
        endpoint = config.endpoint
        bucket = config.bucket
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return f"{endpoint}/{bucket}"
        else:
            return f"https://{bucket}.{endpoint}"

    @staticmethod
    def build_endpoint(endpoint: str) -> str:
        """确保endpoint格式正确并添加协议前缀"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"https://{endpoint}"

    @staticmethod
    def create_client(config: S3FileClientConfig) -> boto3.client:
        """创建华为云OBS客户端"""
        endpoint = HuaweiObsHelper.build_endpoint(config.endpoint)
        region = config.region
        if not region:
            region = HuaweiObsHelper.extract_region_from_endpoint(config.endpoint)
        s3_config = boto3.session.Config(
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
        """上传文件到华为云OBS，处理特殊错误情况"""
        try:
            await asyncio.to_thread(
                client.put_object, Bucket=bucket, Key=key, Body=content, ContentType=file_type
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", "")
            if error_code == "NoSuchBucket":
                raise IOError(f"华为云OBS错误: 存储桶 '{bucket}' 不存在或没有访问权限") from e
            elif error_code == "XAmzContentSHA256Mismatch" or (
                "SHA256Mismatch" in error_message and "sha256" in error_message.lower()
            ):
                current_region = client.meta.region_name if client else "未知"
                current_endpoint = client.meta.endpoint_url if client else "未知"
                detailed_msg = f"华为云OBS SHA256校验失败: {error_message}\n当前客户端已尝试使用 Signature Version 's3' (SigV2) 进行连接。\n如果问题依旧存在, 请检查以下几点:\n1. Boto3 及 Botocore 库是否为最新版本 (可尝试执行: pip install boto3 botocore --upgrade)。\n2. 确认华为云OBS配置中的区域 (当前region: '{current_region}') 和端点 (当前endpoint: '{current_endpoint}') 是否完全正确无误。\n3. Bucket名称 ('{bucket}') 是否符合华为云规范且存在。\n4. 考虑联系华为云技术支持或查阅其官方SDK的最佳实践。"
                raise IOError(detailed_msg) from e
            else:
                raise
