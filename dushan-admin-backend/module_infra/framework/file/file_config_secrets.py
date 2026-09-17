class FileConfigSecrets:
    @staticmethod
    def public(values):
        return {
            key: value
            for key, value in values.items()
            if key not in {"password", "access_key", "access_secret", "accessKey", "accessSecret"}
        }
