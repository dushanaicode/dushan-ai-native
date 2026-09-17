-- simple 初始数据适配 Native；只写业务目录，不写外部服务凭据。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `infra_mq` (`id`, `topic`, `consumer`, `retry_count`, `description`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `enabled`, `concurrency`, `prefetch`) VALUES
(1891372849213450001, 'sms:send', 'system.sms.send', 3, '短信发送消息。由 SmsProducer 投递，SmsSendConsumer 消费。完整链路：模板校验 → 参数构建 → 日志记录 → MQ 投递 → 实际发送。', 'system', NOW(), 'system', NOW(), b'0', 1, NULL, NULL);

INSERT IGNORE INTO `infra_mq` (`id`, `topic`, `consumer`, `retry_count`, `description`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `enabled`, `concurrency`, `prefetch`) VALUES
(1891372849213450002, 'mail:send', 'system.mail.send', 3, '邮件发送消息。由 MailProducer 投递，MailSendConsumer 消费。支持单发、多收件人、批量发送模式。', 'system', NOW(), 'system', NOW(), b'0', 1, NULL, NULL);
