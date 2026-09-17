from __future__ import annotations

import hashlib
import random
import string
from datetime import datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo


class CosAuthUrlGenerator:
    def __init__(self, config_data):
        """
        初始化自定义鉴权URL生成器。
        鉴权加密配置说明: https://cloud.tencent.com/document/product/228/41622
        参数:
        config_data (dict): 包含鉴权配置的字典。
                           预期键值可能包括: 'authType', 'domain', 'encryptionAlgorithm',
                                          'mainKey', 'sign' (TypeA, TypeD query param name),
                                          'effectiveTime', 'signT' (TypeD time query param name),
                                          'timeFormat' (TypeD time format).
        """
        self.config_data = config_data
        self.domain_name = str(self.config_data.get("domain", ""))
        self.encryption_algorithm = self.config_data.get("encryptionAlgorithm", "md5")

    @staticmethod
    def _generate_random_string(length=20):
        characters = string.ascii_letters + string.digits
        return "".join((random.choice(characters) for _ in range(length)))

    def _generate_hash(self, data_str, algorithm_override=None):
        """根据指定算法生成哈希值"""
        algorithm_to_use = algorithm_override if algorithm_override else self.encryption_algorithm
        if algorithm_to_use == "md5":
            return hashlib.md5(data_str.encode("utf-8")).hexdigest()
        elif algorithm_to_use == "sha256":
            return hashlib.sha256(data_str.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm_to_use}")

    @staticmethod
    def _get_eastern_expiration_time(effective_time_seconds):
        """获取东八区的过期时间对象"""
        eastern_tz = ZoneInfo("Asia/Shanghai")
        current_time_eastern = datetime.now(eastern_tz)
        return current_time_eastern + timedelta(seconds=effective_time_seconds)

    def generate_signed_url(self, file_key):
        """
        根据配置的 authType 生成对应的鉴权URL。

        参数:
        file_key (str): 文件在存储中的唯一标识符 (例如: 'path/to/your/file.jpg')。

        返回:
        str: 生成的鉴权URL。
        """
        auth_type = self.config_data.get("authType", "")
        if auth_type == "TypeA":
            return self._generate_type_a_url(file_key)
        elif auth_type == "TypeB":
            return self._generate_type_b_url(file_key)
        elif auth_type == "TypeC":
            return self._generate_type_c_url(file_key)
        elif auth_type == "TypeD":
            return self._generate_type_d_url(file_key)
        else:
            raise ValueError(f"Unsupported authType: '{auth_type}'")

    def _generate_type_a_url(self, file_key):
        """
        TypeA : https://cloud.tencent.com/document/product/228/41623
        """
        pkey = self.config_data.get("mainKey")
        sign_param_name = self.config_data.get("sign", "sign")
        effective_time = int(self.config_data.get("effectiveTime", 0))
        expiration_datetime_eastern = self._get_eastern_expiration_time(effective_time)
        timestamp = int(expiration_datetime_eastern.timestamp())
        rand = self._generate_random_string(20)
        uid = "0"
        signed_path_part = file_key if file_key.startswith("/") else f"/{file_key}"
        sign_str = f"{signed_path_part}-{timestamp}-{rand}-{uid}-{pkey}"
        signature_hash = self._generate_hash(sign_str)
        base_url = urljoin(
            self.domain_name + ("" if self.domain_name.endswith("/") else "/"), file_key.lstrip("/")
        )
        auth_url = f"{base_url}?{sign_param_name}={timestamp}-{rand}-{uid}-{signature_hash}"
        return auth_url

    def _generate_type_b_url(self, file_key):
        """
        TypeB : https://cloud.tencent.com/document/product/228/41871
        """
        pkey = self.config_data.get("mainKey")
        effective_time = int(self.config_data.get("effectiveTime", 0))
        expiration_datetime_eastern = self._get_eastern_expiration_time(effective_time)
        timestamp_str = expiration_datetime_eastern.strftime("%Y%m%d%H%M")
        signed_path_part = file_key if file_key.startswith("/") else f"/{file_key}"
        sign_str = f"{pkey}{timestamp_str}{signed_path_part}"
        signature_hash = self._generate_hash(sign_str)
        base_domain = self.domain_name.rstrip("/") + "/"
        url_path = f"{timestamp_str}/{signature_hash}/{file_key.lstrip('/')}"
        auth_url = urljoin(base_domain, url_path)
        return auth_url

    def _generate_type_c_url(self, file_key):
        """
        TypeC : https://cloud.tencent.com/document/product/228/41624
        """
        pkey = self.config_data.get("mainKey")
        effective_time = int(self.config_data.get("effectiveTime", 0))
        expiration_datetime_eastern = self._get_eastern_expiration_time(effective_time)
        timestamp_hex = hex(int(expiration_datetime_eastern.timestamp()))[2:]
        sign_str = f"{pkey}{file_key}{timestamp_hex}"
        signature_hash = self._generate_hash(sign_str)
        base_domain = self.domain_name.rstrip("/") + "/"
        url_path = f"{signature_hash}/{timestamp_hex}/{file_key.lstrip('/')}"
        auth_url = urljoin(base_domain, url_path)
        return auth_url

    def _generate_type_d_url(self, file_key):
        """
        TypeD : https://cloud.tencent.com/document/product/228/41625
        """
        pkey = self.config_data.get("mainKey")
        sign_param_name = self.config_data.get("sign", "sign")
        time_param_name = self.config_data.get("signT", "t")
        time_format = self.config_data.get("timeFormat")
        effective_time = int(self.config_data.get("effectiveTime", 0))
        expiration_datetime_eastern = self._get_eastern_expiration_time(effective_time)
        if time_format == "16":
            timestamp_val_str = hex(int(expiration_datetime_eastern.timestamp()))[2:]
        else:
            timestamp_val_str = str(int(expiration_datetime_eastern.timestamp()))
        sign_str = f"{pkey}{file_key}{timestamp_val_str}"
        signature_hash = self._generate_hash(sign_str)
        base_url = urljoin(
            self.domain_name + ("" if self.domain_name.endswith("/") else "/"), file_key.lstrip("/")
        )
        auth_url = (
            f"{base_url}?{sign_param_name}={signature_hash}&{time_param_name}={timestamp_val_str}"
        )
        return auth_url
