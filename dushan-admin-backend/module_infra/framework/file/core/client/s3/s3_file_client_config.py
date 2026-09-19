from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from framework.common.validator import URL, NotNull
from module_infra.framework.file.core.client.file_client_config import FileClientConfig

ENDPOINT_QINIU: str = "qiniucs.com"
ENDPOINT_ALIYUN: str = "aliyuncs.com"
ENDPOINT_TENCENT: str = "myqcloud.com"
ENDPOINT_VOLCES: str = "volces.com"
ENDPOINT_HUAWEI: str = "hwclouds.com"
ENDPOINT_MINIO: str = "minio"


class S3FileClientConfig(FileClientConfig):
    """
    S3 文件客户端的配置类
    支持各种兼容S3协议的云存储服务:

    1. AWS S3: 亚马逊对象存储
    2. 阿里云OSS: 阿里云对象存储服务
    3. 腾讯云COS: 腾讯云对象存储
    4. 七牛云: 七牛云对象存储
    5. 华为云OBS: 华为云对象存储
    6. 火山引擎TOS: 字节跳动火山引擎对象存储
    7. MinIO: 开源对象存储

    各云存储服务的相关文档:

    * 自定义域名
    * 1. MinIO：
    * 2. 阿里云：https://help.aliyun.com/document_detail/31836.html
    * 3. 腾讯云：https://cloud.tencent.com/document/product/436/11142
    * 4. 七牛云：https://developer.qiniu.com/kodo/8556/set-the-custom-source-domain-name
    * 5. 华为云：https://support.huaweicloud.com/usermanual-obs/obs_03_0032.html
    * 6. 火山云：https://www.volcengine.com/docs/6349/128983

    * 节点地址
    * 1. MinIO：
    * 2. 阿里云：https://help.aliyun.com/document_detail/31837.html
    * 3. 腾讯云：https://cloud.tencent.com/document/product/436/6224
    * 4. 七牛云：https://developer.qiniu.com/kodo/4088/s3-access-domainname
    * 5. 华为云：https://console.huaweicloud.com/apiexplorer/#/endpoint/OBS
    * 6. 火山云：https://www.volcengine.com/docs/6349/107356

    * 访问 Key
    * 1. MinIO：
    * 2. 阿里云：https://ram.console.aliyun.com/manage/ak
    * 3. 腾讯云：https://console.cloud.tencent.com/cam/capi
    * 4. 七牛云：https://portal.qiniu.com/user/key
    * 5. 华为云：https://console.huaweicloud.com/iam/?region=cn-north-4&locale=zh-cn#/mine/accessKey
    * 6. 火山云：https://console.volcengine.com/iam/keymanage/
    """

    endpoint: str = Field(
        ...,
        description="节点地址 (例如 's3.us-west-2.amazonaws.com' 或 'oss-cn-hangzhou.aliyuncs.com')",
    )
    bucket: str = Field(..., description="存储 Bucket")
    access_key: str = Field(..., description="访问 Key")
    access_secret: str = Field(..., description="访问 Secret")
    region: str | None = Field(None, description="访问 region (某些 S3 提供商需要, 如腾讯云)")
    domain: str | None = Field(None, description="自定义域名 (可选)")
    enable_path_style_access: bool = Field(
        False, description="是否启用 PathStyle 风格访问 (默认为虚拟主机风格)"
    )

    @field_validator("endpoint", mode="before")
    @classmethod
    def _validate_endpoint(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="endpoint", value=v, error_msg="endpoint 不能为空")
        return v

    @field_validator("bucket", mode="before")
    @classmethod
    def _validate_bucket(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="bucket", value=v, error_msg="bucket 不能为空")
        return v

    @field_validator("access_key", mode="before")
    @classmethod
    def _validate_access_key(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="access_key", value=v, error_msg="access_key 不能为空")
        return v

    @field_validator("access_secret", mode="before")
    @classmethod
    def _validate_access_secret(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="access_secret", value=v, error_msg="access_secret 不能为空"
        )
        return v

    @field_validator("domain", mode="before")
    @classmethod
    def _validate_domain(cls, v: Any) -> Any:
        if v is not None and v.strip() != "":
            URL.require_url(field_name="domain", value=str(v), error_msg="domain 必须是 URL 格式")
        return v

    @model_validator(mode="after")
    def validate_qiniu_domain(self) -> "Self":
        """
        在字段验证后执行：如果是七牛云endpoint，则domain不能为空。
        """
        if self.endpoint and ENDPOINT_QINIU in self.endpoint and (not self.domain):
            raise ValueError(
                f"对于七牛云 (endpoint 包含 '{ENDPOINT_QINIU}'), domain 不能为空且必须是有效的 URL"
            )
        return self
