from __future__ import annotations

import asyncio

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig


class TencentCosHelper:
    """腾讯云COS辅助类，提供COS专用的客户端初始化和上传操作"""

    @staticmethod
    def build_domain(config: S3FileClientConfig) -> str:
        """根据配置构建腾讯云COS的访问域名"""
        bucket = config.bucket
        endpoint = config.endpoint
        parts = endpoint.split(".")
        region = config.region or "ap-shanghai"
        if len(parts) >= 3:
            region = parts[1]
        return f"https://{bucket}.cos.{region}.myqcloud.com"

    @staticmethod
    def build_endpoint(endpoint: str, region: str) -> str:
        """确保endpoint格式正确并添加协议前缀"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        parts = endpoint.split(".")
        if len(parts) >= 3 and parts[0] != "cos":
            endpoint = f"cos.{region}.myqcloud.com"
        return f"https://{endpoint}"

    @staticmethod
    def create_client(config: S3FileClientConfig) -> boto3.client:
        """创建腾讯云COS客户端"""
        region = config.region or "ap-shanghai"
        endpoint = config.endpoint
        if not endpoint.startswith("https://cos."):
            endpoint = f"https://cos.{region}.myqcloud.com"
        boto_client_config = BotoConfig(
            s3={"addressing_style": "virtual"},
            signature_version="s3",
            retries={"max_attempts": 3, "mode": "standard"},
        )
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.access_secret,
            region_name=region,
            config=boto_client_config,
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
        """上传文件到腾讯云COS，处理特殊错误情况"""
        try:
            await asyncio.to_thread(
                client.put_object, Bucket=bucket, Key=key, Body=content, ContentType=file_type
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", "")
            if error_code == "PathStyleDomainForbidden":
                raise IOError(
                    "腾讯云COS错误: 必须使用虚拟主机风格访问，请检查配置和客户端初始化方式"
                ) from e
            else:
                raise IOError(error_message) from e
