import type {
  VbenFormProps as FormProps,
  VbenFormSchema as FormSchema,
  FormValues,
} from '@vben/common-ui';

import type { NativeRequestConfig } from '../api/response';
import type { ComponentPropsMap, ComponentType } from './component';

import { setupVbenForm, useVbenForm as useForm, z } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { formRules } from './form-rules';
import { FormSubmission } from './form-submission';

async function initSetupVbenForm() {
  setupVbenForm<ComponentType>({
    config: {
      modelPropNameMap: {
        Upload: 'fileList',
        CheckboxGroup: 'model-value',
      },
    },
    rules: formRules,
  });
}

function useVbenForm<
  TFormValues extends FormValues = FormValues,
  TSubmitValues extends FormValues = TFormValues,
>(
  options: FormProps<
    ComponentType,
    ComponentPropsMap,
    TFormValues,
    TSubmitValues
  >,
) {
  const [Form, formApi] = useForm<
    TFormValues,
    ComponentType,
    ComponentPropsMap,
    TSubmitValues
  >(options);
  const submission = new FormSubmission(formApi, (message) => {
    ElMessage.error(message);
  });
  return [
    Form,
    Object.assign(formApi, {
      submitRequest: <T>(
        request: (config: NativeRequestConfig) => Promise<T>,
        settings?: { showSummary?: boolean },
      ) => submission.submit(request, settings),
    }),
  ] as const;
}

export { initSetupVbenForm, useVbenForm, z };

export type VbenFormSchema<TValues extends FormValues = FormValues> =
  FormSchema<ComponentType, ComponentPropsMap, TValues>;
export type VbenFormProps<
  TFormValues extends FormValues = FormValues,
  TSubmitValues extends FormValues = TFormValues,
> = FormProps<ComponentType, ComponentPropsMap, TFormValues, TSubmitValues>;
