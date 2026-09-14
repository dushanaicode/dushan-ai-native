import { z } from '@vben/common-ui';

const identifier = z.string().regex(/^[A-Za-z0-9][\w.:-]{0,127}$/);
const commandSchema = z
  .object({
    type: identifier,
    payload: z.unknown().optional(),
    requestId: identifier.optional(),
    senderId: identifier.optional(),
    timestamp: z.number().nonnegative().optional(),
  })
  .strict();
const messageSchema = commandSchema.extend({
  timestamp: z.number().nonnegative(),
});

export type SocketCommand = z.infer<typeof commandSchema>;
export type SocketMessage = z.infer<typeof messageSchema>;
export interface SocketProtocol {
  encode: (command: SocketCommand) => string;
  parse: (data: unknown) => SocketMessage;
}

export const socketProtocol: SocketProtocol = {
  encode(command) {
    return JSON.stringify(commandSchema.parse(command));
  },
  parse(data) {
    if (typeof data !== 'string')
      throw new TypeError('WebSocket 只接收文本消息');
    let value: unknown;
    try {
      value = JSON.parse(data);
    } catch {
      throw new TypeError('WebSocket 消息不是有效 JSON');
    }
    const result = messageSchema.safeParse(value);
    // 不把原始消息放入错误，避免日志暴露业务内容。
    if (!result.success) throw new TypeError('WebSocket 消息字段不符合协议');
    return result.data;
  },
};
