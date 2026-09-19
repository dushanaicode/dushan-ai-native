import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** MQ 消费日志端点（`/infra/mq/log`）。ID 均为雪花字符串。 */
export namespace InfraMqLogApi {
  /** MQ 消息日志信息 RespVO */
  export interface MqLogRespVO {
    beginTime: string;
    consumer: string;
    createTime: string;
    duration?: number;
    endTime?: string;
    executeIndex: number;
    id: string;
    messageId: string;
    payload?: unknown;
    result?: string;
    status: number;
    topic: string;
  }

  /** MQ 消息日志分页查询 ReqVO */
  export interface MqLogPageReqVO extends PageParam {
    beginTime?: string;
    consumer?: string;
    endTime?: string;
    messageId?: string;
    status?: number;
  }
}

/** 获得消费日志 */
export async function getMqLog(id: string) {
  return requestClient.get<InfraMqLogApi.MqLogRespVO>(
    `/infra/mq/log/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得消费日志分页 */
export async function getMqLogPage(params: InfraMqLogApi.MqLogPageReqVO) {
  return requestClient.get<PageResult<InfraMqLogApi.MqLogRespVO>>(
    '/infra/mq/log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取MQ日志可导出字段列表 */
export async function getExportMqLogFields() {
  return requestClient.get<ExportField[]>('/infra/mq/log/export-fields');
}

/** 导出MQ日志 */
export async function exportMqLog(params: InfraMqLogApi.MqLogPageReqVO) {
  return requestClient.download('/infra/mq/log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
