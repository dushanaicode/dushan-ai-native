import { Buffer } from 'node:buffer';
import { readFileSync } from 'node:fs';
import { request } from 'node:http';

import { expect, it } from 'vitest';

import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import {
  buildSocketUrl,
  classifySocketClose,
  defaultSocketPolicy,
  SocketConnection,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/websocket/connection';
import { socketProtocol } from '../../dushan-admin-frontend/apps/web-ele/src/services/websocket/protocol';
import { Window } from '../../dushan-admin-frontend/node_modules/happy-dom/lib/index.js';

const scenarioPath = process.env.DUSHAN_WS_FRONTEND_CASE_FILE;

it.skipIf(!scenarioPath)(
  '真实 SocketConnection 经 HTTP 取票后与本地 ASGI 服务往返',
  async () => {
    if (!scenarioPath) throw new Error('缺少真实客户端测试配置');
    const scenario = JSON.parse(readFileSync(scenarioPath, 'utf8')) as {
      origin: string;
      port: number;
      token: string;
    };
    const browser = new Window({ url: scenario.origin });
    const errors: unknown[] = [];
    const scope = { generation: 'live-test', token: scenario.token };
    const session = new SessionCoordinator({
      read: () => scope,
      write: () => {},
      refresh: async () => scenario.token,
      expire: async () => {},
      lock: (operation) => operation(),
      subscribe: () => () => {},
    });
    let ticketRequests = 0;
    const socket = new SocketConnection({
      baseUrl: new URL(`ws://127.0.0.1:${scenario.port}/api/ws`),
      session,
      protocol: socketProtocol,
      buildUrl: (base, ticket) => buildSocketUrl(base, ticket, 'test'),
      classifyClose: classifySocketClose,
      policy: {
        ...defaultSocketPolicy,
        heartbeatIntervalMs: 50,
        heartbeatTimeoutMs: 1000,
      },
      onError: (error) => errors.push(error),
      createSocket: (url) => new browser.WebSocket(url) as unknown as WebSocket,
      getTicket: (signal) =>
        new Promise((resolve, reject) => {
          ticketRequests += 1;
          const operation = request(
            `http://127.0.0.1:${scenario.port}/api/ws-test/ticket`,
            {
              method: 'POST',
              headers: { Authorization: `Bearer ${scenario.token}` },
            },
            async (response) => {
              signal.removeEventListener('abort', cancel);
              try {
                const chunks = [];
                for await (const chunk of response) chunks.push(chunk);
                if (response.statusCode !== 200)
                  throw new Error('测试取票失败');
                resolve(JSON.parse(Buffer.concat(chunks).toString()));
              } catch (error) {
                reject(error);
              }
            },
          );
          const cancel = () => operation.destroy(new Error('取票取消'));
          signal.addEventListener('abort', cancel, { once: true });
          operation.on('error', reject);
          operation.end();
        }),
    });
    const connected = Promise.withResolvers<boolean>();
    const received = Promise.withResolvers<unknown>();
    socket.onConnected(() => connected.resolve(true));
    socket.on('echo', (message) => received.resolve(message));
    try {
      await socket.connect();
      await connected.promise;
      socket.send({
        type: 'echo',
        requestId: 'frontend-live',
        payload: { text: 'real-client' },
      });
      expect(await received.promise).toMatchObject({
        type: 'echo',
        requestId: 'frontend-live',
        payload: { text: 'real-client' },
      });
      expect(ticketRequests).toBe(1);
      expect(socket.status).toBe('open');
      expect(errors).toEqual([]);
    } finally {
      socket.dispose();
      session.dispose();
      await browser.happyDOM.close();
    }
  },
  15_000,
);
