from framework.common.enums import BaseEnum


class SocialTypeEnum(BaseEnum):
    ALIPAY = (10, "ALIPAY")
    DINGTALK = (20, "DINGTALK")
    WECHAT_ENTERPRISE = (30, "WECHAT_ENTERPRISE")
    WECHAT_MP = (31, "WECHAT_MP")
    WECHAT_OPEN = (32, "WECHAT_OPEN")
    WECHAT_MINI_PROGRAM = (33, "WECHAT_MINI_PROGRAM")
    WECHAT_ENTERPRISE_V2 = (34, "WECHAT_ENTERPRISE_V2")
    ALIPAY_CERT = (40, "ALIPAY_CERT")
    ALIYUN = (41, "ALIYUN")
    APPLE = (42, "APPLE")
    BAIDU = (43, "BAIDU")
    CSDN = (44, "CSDN")
    DINGTALK_ACCOUNT = (45, "DINGTALK_ACCOUNT")
    DINGTALK_V2 = (46, "DINGTALK_V2")
    DISCORD = (47, "DISCORD")
    DOUYIN = (48, "DOUYIN")
    ELEME = (49, "ELEME")
    FEISHU = (50, "FEISHU")
    GITEE = (51, "GITEE")
    GITLAB = (52, "GITLAB")
    GITHUB = (53, "GITHUB")
    GOOGLE = (54, "GOOGLE")
    HUAWEI = (55, "HUAWEI")
    HUAWEI_V3 = (56, "HUAWEI_V3")
    JD = (57, "JD")
    LINKEDIN = (58, "LINKEDIN")
    MEITUAN = (59, "MEITUAN")
    MICROSOFT = (60, "MICROSOFT")
    QQ_MINI_PROGRAM = (61, "QQ_MINI_PROGRAM")
    QQ = (62, "QQ")
    SLACK = (63, "SLACK")
    TAOBAO = (64, "TAOBAO")
    TOUTIAO = (65, "TOUTIAO")
    WECHAT_ENTERPRISE_CORP_APP = (66, "WECHAT_ENTERPRISE_CORP_APP")
    WEIBO = (67, "WEIBO")
    MI = (68, "MI")

    @property
    def auth_source(self) -> str:
        return "WECHAT_ENTERPRISE_WEB" if self is self.WECHAT_ENTERPRISE_V2 else self.label
