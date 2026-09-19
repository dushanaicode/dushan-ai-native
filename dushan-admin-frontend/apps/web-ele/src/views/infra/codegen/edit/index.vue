<script lang="ts" setup>
import type { InfraCodegenApi } from '#/api/infra/codegen';
import type { StepWizardExposes } from '#/components';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElLoading, ElMessage } from 'element-plus';

import { getCodegenDetail, updateCodegen } from '#/api/infra/codegen';
import { StepWizard } from '#/components';
import { InfraCodegenTemplateTypeEnum } from '#/constants/enums';
import { $t } from '#/locales';

import BasicInfo from '../modules/basic-info.vue';
import ColumnInfo from '../modules/column-info.vue';
import GenerationInfo from '../modules/generation-info.vue';

defineOptions({ name: 'InfraCodegenEdit' });

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const currentStep = ref(0);
const detail = ref<InfraCodegenApi.CodegenDetailRespVO>();
const wizardRef = ref<StepWizardExposes>();
const basicInfoRef = ref<InstanceType<typeof BasicInfo>>();
const columnInfoRef = ref<InstanceType<typeof ColumnInfo>>();
const generationInfoRef = ref<InstanceType<typeof GenerationInfo>>();

const steps = [
  { title: '基本信息' },
  { title: '字段配置' },
  { title: '生成配置' },
];

const table = computed(() => detail.value?.table);
const columns = computed(() => detail.value?.columns || []);
const isFirstStep = computed(() => currentStep.value === 0);
const isLastStep = computed(() => currentStep.value === steps.length - 1);
const pageTitle = computed(() =>
  table.value ? `代码生成配置 - ${table.value.tableName}` : '代码生成配置',
);

function toRequiredString(value: unknown, fallback: string) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text || fallback;
}

function toNullableString(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function toNumber(value: unknown, fallback: number) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : fallback;
}

function toBoolean(value: unknown, fallback: boolean) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (value === 'true' || value === 1 || value === '1') {
    return true;
  }
  if (value === 'false' || value === 0 || value === '0') {
    return false;
  }
  return fallback;
}

function normalizeTemplateFields(
  values: Partial<InfraCodegenApi.CodegenTableRespVO>,
  templateType: number,
) {
  if (templateType === InfraCodegenTemplateTypeEnum.TREE) {
    return {
      masterTableId: null,
      subJoinColumnId: null,
      subJoinMany: null,
      treeNameColumnId: toNullableString(values.treeNameColumnId),
      treeParentColumnId: toNullableString(values.treeParentColumnId),
    };
  }

  if (templateType === InfraCodegenTemplateTypeEnum.SUB) {
    return {
      masterTableId: toNullableString(values.masterTableId),
      subJoinColumnId: toNullableString(values.subJoinColumnId),
      subJoinMany: toBoolean(values.subJoinMany, true),
      treeNameColumnId: null,
      treeParentColumnId: null,
    };
  }

  return {
    masterTableId: null,
    subJoinColumnId: null,
    subJoinMany: null,
    treeNameColumnId: null,
    treeParentColumnId: null,
  };
}

function normalizeCodegenUpdatePayload(
  originalTable: InfraCodegenApi.CodegenTableRespVO,
  basicValues: Partial<InfraCodegenApi.CodegenTableRespVO> = {},
  generationValues: Partial<InfraCodegenApi.CodegenTableRespVO> = {},
  columnValues: InfraCodegenApi.CodegenColumnRespVO[] = [],
): InfraCodegenApi.CodegenUpdateReqVO {
  const templateType = toNumber(
    generationValues.templateType,
    originalTable.templateType,
  );
  const templateFields = normalizeTemplateFields(
    generationValues,
    templateType,
  );

  return {
    columns: columnValues.map((column) => ({
      columnComment: column.columnComment,
      columnName: column.columnName,
      createOperation: column.createOperation,
      dataType: column.dataType,
      dictType: toNullableString(column.dictType),
      example: toNullableString(column.example),
      fieldName: column.fieldName,
      fieldType: column.fieldType,
      htmlType: column.htmlType,
      id: column.id,
      listOperation: column.listOperation,
      listOperationCondition: column.listOperationCondition,
      listOperationResult: column.listOperationResult,
      nullable: column.nullable,
      orderNo: column.orderNo,
      primaryKey: column.primaryKey,
      tableId: column.tableId,
      updateOperation: column.updateOperation,
    })),
    table: {
      author: toNullableString(basicValues.author ?? originalTable.author),
      createTime: originalTable.createTime ?? null,
      dataSourceConfigId: originalTable.dataSourceConfigId,
      businessName: toRequiredString(
        generationValues.businessName,
        originalTable.businessName,
      ),
      classComment: toRequiredString(
        generationValues.classComment,
        originalTable.classComment,
      ),
      className: toRequiredString(
        basicValues.className,
        originalTable.className,
      ),
      enableExport: toBoolean(
        generationValues.enableExport,
        originalTable.enableExport,
      ),
      frontType: toNumber(generationValues.frontType, originalTable.frontType),
      id: originalTable.id,
      moduleName: toRequiredString(
        generationValues.moduleName,
        originalTable.moduleName,
      ),
      parentMenuId: toNullableString(
        generationValues.parentMenuId ?? originalTable.parentMenuId,
      ),
      remark: toNullableString(basicValues.remark ?? originalTable.remark),
      scene: toNumber(generationValues.scene, originalTable.scene),
      tableComment: toRequiredString(
        basicValues.tableComment,
        originalTable.tableComment,
      ),
      tableName: toRequiredString(
        basicValues.tableName,
        originalTable.tableName,
      ),
      templateType,
      updateTime: originalTable.updateTime ?? null,
      ...templateFields,
    },
  };
}

function parseTableId() {
  const raw = route.query.id;
  const first = Array.isArray(raw) ? raw[0] : raw;
  const tableId = typeof first === 'string' ? first : undefined;
  return tableId || undefined;
}

async function loadDetail() {
  const tableId = parseTableId();
  if (!tableId) {
    ElMessage.error('缺少代码生成表编号');
    await router.push('/infra/codegen');
    return;
  }

  loading.value = true;
  try {
    detail.value = await getCodegenDetail(tableId);
  } finally {
    loading.value = false;
  }
}

async function validateCurrentStep() {
  if (currentStep.value === 0) {
    return await basicInfoRef.value?.validate();
  }

  if (currentStep.value === 2) {
    return await generationInfoRef.value?.validate();
  }

  return true;
}

async function handleNext() {
  const valid = await validateCurrentStep();
  if (!valid) return;

  wizardRef.value?.setStep(currentStep.value + 1);
}

function handlePrev() {
  wizardRef.value?.setStep(currentStep.value - 1);
}

async function handleBack() {
  await router.push('/infra/codegen');
}

async function handleSubmit() {
  const tableData = table.value;
  if (!tableData) return;

  const basicValid = await basicInfoRef.value?.validate();
  if (!basicValid) {
    wizardRef.value?.setStep(0);
    return;
  }

  const generationValid = await generationInfoRef.value?.validate();
  if (!generationValid) {
    wizardRef.value?.setStep(2);
    return;
  }

  const basicValues = await basicInfoRef.value?.getData();
  const generationValues = await generationInfoRef.value?.getData();
  const columnValues = columnInfoRef.value?.getData() || [];

  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.updating', [tableData.tableName]),
  });

  try {
    await updateCodegen(
      normalizeCodegenUpdatePayload(
        tableData,
        basicValues,
        generationValues,
        columnValues,
      ),
    );
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    await router.push('/infra/codegen');
  } finally {
    loadingInstance.close();
  }
}

onMounted(() => {
  void loadDetail();
});
</script>

<template>
  <Page auto-content-height :title="pageTitle">
    <div v-loading="loading" class="codegen-edit">
      <StepWizard
        ref="wizardRef"
        v-model:current="currentStep"
        clickable
        :loading="loading"
        mode="default"
        :show-actions="false"
        :show-step-info="false"
        :steps="steps"
      >
        <template #step-0>
          <BasicInfo ref="basicInfoRef" :table="table" />
        </template>

        <template #step-1>
          <ColumnInfo ref="columnInfoRef" :columns="columns" />
        </template>

        <template #step-2>
          <GenerationInfo
            ref="generationInfoRef"
            :columns="columns"
            :table="table"
          />
        </template>
      </StepWizard>

      <div class="codegen-edit__actions">
        <ElButton @click="handleBack">返回</ElButton>
        <ElButton v-show="!isFirstStep" @click="handlePrev">上一步</ElButton>
        <ElButton v-if="!isLastStep" type="primary" @click="handleNext">
          下一步
        </ElButton>
        <ElButton v-else type="primary" @click="handleSubmit">保存</ElButton>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.codegen-edit {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
  padding: 16px;
}

.codegen-edit__actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
