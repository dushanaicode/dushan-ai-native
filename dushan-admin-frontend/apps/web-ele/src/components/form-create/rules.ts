import type { DragRule } from '@form-create/designer';

import { $t } from '#/locales';
import { createRandomId } from '#/utils/random-id';

export function nativeFormRules(): DragRule[] {
  return [
    {
      name: 'NativeUserSelect',
      label: 'user',
      props: [
        { type: 'switch', field: 'multiple', title: $t('infraTools.multiple') },
      ],
    },
    {
      name: 'NativeDeptSelect',
      label: 'department',
      props: [
        { type: 'switch', field: 'multiple', title: $t('infraTools.multiple') },
      ],
    },
    {
      name: 'NativeDictSelect',
      label: 'dictionary',
      props: [
        {
          type: 'input',
          field: 'dictType',
          title: $t('infraTools.dictType'),
        },
        {
          type: 'select',
          field: 'valueType',
          title: $t('infraTools.valueType'),
          value: 'string',
          options: [
            { label: 'String', value: 'string' },
            { label: 'Number', value: 'number' },
          ],
        },
        { type: 'switch', field: 'multiple', title: $t('infraTools.multiple') },
      ],
    },
    {
      name: 'NativeApiSelect',
      label: 'apiSelect',
      props: [
        {
          type: 'input',
          field: 'apiPath',
          title: $t('infraTools.apiPath'),
          props: { placeholder: '/system/user/simple-list' },
        },
        {
          type: 'input',
          field: 'labelField',
          title: $t('infraTools.labelField'),
          value: 'name',
        },
        {
          type: 'input',
          field: 'valueField',
          title: $t('infraTools.valueField'),
          value: 'id',
        },
        { type: 'switch', field: 'multiple', title: $t('infraTools.multiple') },
      ],
    },
    { name: 'NativeFileUpload', label: 'file', props: [] },
    { name: 'NativeImageUpload', label: 'image', props: [] },
    { name: 'NativeImagesUpload', label: 'images', props: [] },
    { name: 'NativeRichText', label: 'editor', props: [] },
  ].map((entry) => ({
    name: entry.name,
    label: $t(`infraTools.${entry.label}`),
    icon: 'icon-input',
    languageKey: [],
    rule: () => ({
      type: entry.name,
      field: createRandomId(),
      title: $t(`infraTools.${entry.label}`),
      props: {},
    }),
    props: () => entry.props,
  }));
}
