import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** MQ 消息定义端点（`/infra/mq`）。ID 均为雪花字符串。 */
export namespace InfraMqApi {
  /** MQ 消息定义信息 RespVO */
  export interface MqRespVO {
    concurrency?: number;
    consumer: string;
    createTime: string;
    description?: string;
    enabled: boolean;
    id: string;
    prefetch?: number;
    retryCount: number;
    topic: string;
  }

  /** MQ 消息定义创建/修改 ReqVO */
  export interface MqSaveReqVO {
    concurrency?: number;
    consumer: string;
    description?: string;
    enabled?: boolean;
    id?: string;
    prefetch?: number;
    retryCount: number;
    topic: string;
  }

  /** MQ 消息定义分页查询 ReqVO */
  export interface MqPageReqVO extends PageParam {
    consumer?: string;
    createTime?: string[];
    status?: number;
    topic?: string;
  }
}

/** 创建消息定义 */
export async function createMq(data: InfraMqApi.MqSaveReqVO) {
  return requestClient.post('/infra/mq/create', data);
}

/** 更新消息定义 */
export async function updateMq(data: InfraMqApi.MqSaveReqVO) {
  return requestClient.put('/infra/mq/update', data);
}

/** 删除消息定义 */
export async function deleteMq(id: string) {
  return requestClient.delete(`/infra/mq/delete?id=${encodeURIComponent(id)}`);
}

/** 获得消息定义 */
export async function getMq(id: string) {
  return requestClient.get<InfraMqApi.MqRespVO>(
    `/infra/mq/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得消息定义分页 */
export async function getMqPage(params: InfraMqApi.MqPageReqVO) {
  return requestClient.get<PageResult<InfraMqApi.MqRespVO>>('/infra/mq/page', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获取消息定义可导出字段列表 */
export async function getExportMqFields() {
  return requestClient.get<ExportField[]>('/infra/mq/export-fields');
}

/** 导出消息定义 */
export async function exportMq(params: InfraMqApi.MqPageReqVO) {
  return requestClient.download('/infra/mq/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
