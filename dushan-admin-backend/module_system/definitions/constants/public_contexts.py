class PublicContexts:
    TENANT_SELECTION = "system.auth.tenant"
    SOCIAL_LOGIN = "system.auth.social"
    SMS_CALLBACK = "system.sms.callback"

    NAMES = frozenset({TENANT_SELECTION, SOCIAL_LOGIN, SMS_CALLBACK})
