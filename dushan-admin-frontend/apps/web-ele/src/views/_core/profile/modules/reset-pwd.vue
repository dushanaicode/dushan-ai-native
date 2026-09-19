<script setup lang="ts">
import { ElMessage } from 'element-plus';

import { useVbenForm, z } from '#/adapter/form';
import { updateUserProfilePassword } from '#/api/core/profile';
import { $t } from '#/locales';

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    labelWidth: 90,
  },
  handleSubmit: async (values) => {
    await updateUserProfilePassword({
      newPassword: values.newPassword as string,
      oldPassword: values.oldPassword as string,
    });
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    await formApi.resetForm();
  },
  resetButtonOptions: {
    show: false,
  },
  schema: [
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请输入旧密码',
      },
      fieldName: 'oldPassword',
      label: '旧密码',
      rules: z
        .string({ message: '请输入旧密码' })
        .min(4, '密码长度不能少于4位')
        .max(16, '密码长度不能超过16位'),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        passwordStrength: true,
        placeholder: '请输入新密码',
      },
      dependencies: {
        rules(values) {
          return z
            .string({ message: '请输入新密码' })
            .min(4, '密码长度不能少于4位')
            .max(16, '密码长度不能超过16位')
            .refine(
              (value) => value !== values.oldPassword,
              '新密码不能与旧密码相同',
            );
        },
        triggerFields: ['newPassword', 'oldPassword'],
      },
      fieldName: 'newPassword',
      label: '新密码',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请再次输入新密码',
      },
      dependencies: {
        rules(values) {
          return z
            .string({ message: '请再次输入新密码' })
            .min(4, '密码长度不能少于4位')
            .max(16, '密码长度不能超过16位')
            .refine(
              (value) => value === values.newPassword,
              '两次输入的密码不一致',
            );
        },
        triggerFields: ['newPassword', 'confirmPassword'],
      },
      fieldName: 'confirmPassword',
      label: '确认密码',
      rules: 'required',
    },
  ],
  submitButtonOptions: {
    text: '修改密码',
  },
});
</script>

<template>
  <div class="max-w-lg">
    <Form />
  </div>
</template>
