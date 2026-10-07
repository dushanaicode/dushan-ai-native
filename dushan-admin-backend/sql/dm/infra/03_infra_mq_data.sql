-- 由 mysql/infra/03_infra_mq_data.sql 生成；请修改 MySQL 源文件后重新生成。

-- 仅用于空库首次初始化，不支持重复执行。

SET IDENTITY_INSERT infra_mq ON;

INSERT INTO infra_mq (id, topic, consumer, retry_count, description, creator, create_time, updater, update_time, deleted, enabled, concurrency, prefetch) VALUES
(1891372849213450001, 'sms:send', 'system.sms.send', 3, '短信发送消息。由 SmsProducer 投递，SmsSendConsumer 消费。完整链路：模板校验 → 参数构建 → 日志记录 → MQ 投递 → 实际发送。', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1, NULL, NULL);

SET IDENTITY_INSERT infra_mq OFF;

SET IDENTITY_INSERT infra_mq ON;

INSERT INTO infra_mq (id, topic, consumer, retry_count, description, creator, create_time, updater, update_time, deleted, enabled, concurrency, prefetch) VALUES
(1891372849213450002, 'mail:send', 'system.mail.send', 3, '邮件发送消息。由 MailProducer 投递，MailSendConsumer 消费。支持单发、多收件人、批量发送模式。', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1, NULL, NULL);

SET IDENTITY_INSERT infra_mq OFF;
