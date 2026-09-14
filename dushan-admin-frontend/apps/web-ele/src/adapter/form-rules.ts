import { $t } from '@vben/locales';

function isEmpty(value: unknown) {
  return (
    value === undefined ||
    value === null ||
    value === '' ||
    (Array.isArray(value) && value.length === 0)
  );
}

export const formRules = {
  mobile(value: unknown, _params: unknown, ctx: { label?: string }) {
    return (
      isEmpty(value) ||
      (typeof value === 'string' &&
        /^(?:0|86|\+86)?1[3-9]\d{9}$/.test(value)) ||
      $t('utils.formRules.mobile', [ctx.label])
    );
  },
  required(value: unknown, _params: unknown, ctx: { label?: string }) {
    return !isEmpty(value) || $t('ui.formRules.required', [ctx.label]);
  },
  selectRequired(value: unknown, _params: unknown, ctx: { label?: string }) {
    return !isEmpty(value) || $t('ui.formRules.selectRequired', [ctx.label]);
  },
};
