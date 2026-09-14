import type { FormValues } from '@vben/common-ui';
import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { SwitchStatusValue } from '../constants/status';
import type { ComponentPropsMap, ComponentType } from './component';

import { h } from 'vue';

import {
  setupVbenVxeTable,
  useVbenVxeGrid as useGrid,
} from '@vben/plugins/vxe-table';

import { ElButton, ElImage } from 'element-plus';

import DictTag from '../components/dict-tag.vue';
import TagPreview from '../components/tag-preview.vue';
import CellSwitch from './cell-switch.vue';
import { useVbenForm } from './form';

setupVbenVxeTable({
  configVxeTable: (vxeUI) => {
    vxeUI.setConfig({
      grid: {
        align: 'center',
        border: false,
        columnConfig: {
          resizable: true,
        },
        minHeight: 180,
        formConfig: {
          // 全局禁用vxe-table的表单配置，使用formOptions
          enabled: false,
        },
        proxyConfig: {
          autoLoad: true,
          response: {
            result: 'items',
            total: 'total',
            list: 'items',
          },
          showActiveMsg: true,
          showResponseMsg: false,
        },
        round: true,
        showOverflow: true,
        size: 'small',
      } as VxeTableGridOptions,
    });

    // 表格配置项可以用 cellRender: { name: 'CellImage' },
    vxeUI.renderer.add('CellImage', {
      renderTableDefault(renderOpts, params) {
        const { props } = renderOpts;
        const { column, row } = params;
        const src = row[column.field];
        return h(ElImage, { src, previewSrcList: [src], ...props });
      },
    });

    // 表格配置项可以用 cellRender: { name: 'CellLink' },
    vxeUI.renderer.add('CellLink', {
      renderTableDefault(renderOpts) {
        const { props } = renderOpts;
        return h(
          ElButton,
          { size: 'small', link: true },
          { default: () => props?.text },
        );
      },
    });

    vxeUI.renderer.add('CellSwitch', {
      renderTableDefault({ props }, { column, row }) {
        const { change, ...switchProps } = props as {
          change: (
            value: SwitchStatusValue,
            record: typeof row,
          ) => Promise<unknown>;
        };
        return h(CellSwitch, {
          ...switchProps,
          change: (value) => change(value, row),
          modelValue: row[column.field],
          'onUpdate:modelValue': (value) => {
            row[column.field] = value;
          },
        });
      },
    });

    vxeUI.renderer.add('CellTagStyle', {
      renderTableDefault(_options, { column, row }) {
        const tagStyle = row[column.field];
        return tagStyle === null || tagStyle === undefined
          ? ''
          : h(TagPreview, { tagStyle, text: row.label });
      },
    });
    vxeUI.renderer.add('CellDict', {
      renderTableDefault({ props }, { column, row }) {
        const options = props as { type: string };
        return h(DictTag, { ...options, value: row[column.field] });
      },
    });
  },
  useVbenForm,
});

export const useVbenVxeGrid = <
  T extends Record<string, any>,
  TFormValues extends FormValues = FormValues,
  TSubmitValues extends FormValues = TFormValues,
>(
  ...rest: Parameters<
    typeof useGrid<
      T,
      ComponentType,
      ComponentPropsMap,
      TFormValues,
      TSubmitValues
    >
  >
) =>
  useGrid<T, ComponentType, ComponentPropsMap, TFormValues, TSubmitValues>(
    ...rest,
  );

export type * from '@vben/plugins/vxe-table';
