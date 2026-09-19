<script lang="ts" setup>
import type { DiskRow } from '../data';

import { IconifyIcon } from '@vben/icons';

import { ElCard, ElProgress, ElTable, ElTableColumn } from 'element-plus';

import { formatCellValue, getPercentStatus } from '../data';

defineOptions({ name: 'InfraServerDiskCard' });

defineProps<{
  rows: DiskRow[];
}>();
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="flex min-h-8 items-center gap-2">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
        >
          <IconifyIcon icon="lucide:hard-drive" class="size-5" />
        </span>
        <span class="min-w-0 truncate text-base font-semibold">磁盘状态</span>
      </div>
    </template>

    <ElTable :data="rows" border stripe>
      <ElTableColumn label="盘符路径" min-width="140" prop="dirName" />
      <ElTableColumn label="文件系统" min-width="120" prop="sysTypeName" />
      <ElTableColumn label="盘符名称" min-width="180" prop="typeName" />
      <ElTableColumn label="总大小" min-width="100" prop="total" />
      <ElTableColumn label="可用大小" min-width="100" prop="free" />
      <ElTableColumn label="已用大小" min-width="100" prop="used" />
      <ElTableColumn label="已用百分比" min-width="180">
        <template #default="{ row }">
          <div class="flex min-w-0 items-center gap-2">
            <ElProgress
              :percentage="row.usagePercent"
              :show-text="false"
              :status="getPercentStatus(row.usagePercent)"
              :stroke-width="8"
              class="min-w-24 flex-1"
            />
            <span
              :class="row.danger ? 'text-destructive' : 'text-foreground'"
              class="w-12 shrink-0 text-right text-sm"
            >
              {{ formatCellValue(row.usage) }}
            </span>
          </div>
        </template>
      </ElTableColumn>
    </ElTable>
  </ElCard>
</template>
