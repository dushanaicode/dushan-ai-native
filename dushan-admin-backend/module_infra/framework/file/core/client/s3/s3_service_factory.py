from __future__ import annotations

import boto3

from module_infra.framework.file.core.client.s3.aliyun.aliyun_oss_helper import AliyunOssHelper
from module_infra.framework.file.core.client.s3.hwclouds.hwclouds_obs_helper import HuaweiObsHelper
from module_infra.framework.file.core.client.s3.myqcloud.myqcloud_cos_helper import TencentCosHelper
from module_infra.framework.file.core.client.s3.s3_file_client_config import (
    ENDPOINT_ALIYUN,
    ENDPOINT_HUAWEI,
    ENDPOINT_MINIO,
    ENDPOINT_QINIU,
    ENDPOINT_TENCENT,
    ENDPOINT_VOLCES,
    S3FileClientConfig,
)
from module_infra.framework.file.core.client.s3.s3_standard_s3_helper import StandardS3Helper
from module_infra.framework.file.core.client.s3.volces.volces_tos_helper import VolcanoTosHelper


class S3ServiceFactory:
    """S3服务工厂类，根据不同的服务提供商创建对应的Helper类"""

    @classmethod
    def detect_service_type(cls, config: S3FileClientConfig) -> str:
        """根据配置检测S3服务类型"""
        endpoint = config.endpoint.lower()
        if ENDPOINT_ALIYUN in endpoint:
            return "aliyun"
        elif ENDPOINT_TENCENT in endpoint:
            return "tencent"
        elif ENDPOINT_VOLCES in endpoint or "tos-s3" in endpoint:
            return "volcano"
        elif ENDPOINT_HUAWEI in endpoint or "myhuaweicloud.com" in endpoint or "obs." in endpoint:
            return "huawei"
        elif ENDPOINT_QINIU in endpoint:
            return "qiniu"
        elif ENDPOINT_MINIO in endpoint:
            return "minio"
        else:
            return "standard"

    @classmethod
    def get_helper(
        cls, config: S3FileClientConfig
    ) -> type[
        AliyunOssHelper | TencentCosHelper | VolcanoTosHelper | HuaweiObsHelper | StandardS3Helper
    ]:
        """根据服务类型获取对应的Helper类"""
        service_type = cls.detect_service_type(config)
        if service_type == "aliyun":
            config, modified = AliyunOssHelper.check_and_fix_config(config)
            if modified:
                pass
            return AliyunOssHelper
        elif service_type == "tencent":
            return TencentCosHelper
        elif service_type == "volcano":
            return VolcanoTosHelper
        elif service_type == "huawei":
            return HuaweiObsHelper
        elif service_type == "qiniu" or service_type == "minio":
            return StandardS3Helper
        else:
            return StandardS3Helper

    @classmethod
    def create_client(cls, config: S3FileClientConfig) -> boto3.client:
        """根据服务类型创建对应的S3客户端"""
        helper = cls.get_helper(config)
        return helper.create_client(config)

    @classmethod
    def build_domain(cls, config: S3FileClientConfig) -> str:
        """根据服务类型构建访问域名"""
        helper = cls.get_helper(config)
        return helper.build_domain(config)

    @classmethod
    async def upload_file(
        cls,
        client: boto3.client,
        config: S3FileClientConfig,
        key: str,
        content: bytes,
        file_type: str,
    ) -> None:
        """根据服务类型上传文件"""
        helper = cls.get_helper(config)
        await helper.upload_file(client, config.bucket, key, content, file_type)
