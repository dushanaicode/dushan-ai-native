import type { App, Component } from 'vue';

import { h } from 'vue';

import FcDesigner from '@form-create/designer';
import formCreate from '@form-create/element-ui';
import autoImport from '@form-create/element-ui/auto-import';
import {
  ElAside,
  ElBadge,
  ElButton,
  ElCol,
  ElColorPicker,
  ElContainer,
  ElDialog,
  ElDivider,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElForm,
  ElFormItem,
  ElHeader,
  ElInput,
  ElInputNumber,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElPopconfirm,
  ElPopover,
  ElRadioButton,
  ElRadioGroup,
  ElRow,
  ElSelect,
  ElSlider,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElText,
  ElTooltip,
  ElTree,
} from 'element-plus';

import { RichTextarea } from '#/components';

import ApiSelect from './api-select.vue';
import DeptSelect from './dept-select.vue';
import DictSelect from './dict-select.vue';
import FileField from './file-field.vue';
import UserSelect from './user-select.vue';

const installed = new WeakSet<App>();

/** 仅打开设计器或生成表单时安装；复用Native上传、用户与字典端口。 */
export function setupFormCreate(app: App) {
  if (installed.has(app)) return;
  formCreate.use(autoImport);
  app.use(formCreate);
  app.use(FcDesigner);
  // 只注册设计器需要的组件，保留应用现有Vben v-loading指令。
  for (const [name, component] of Object.entries({
    ElAside,
    ElBadge,
    ElButton,
    ElCol,
    ElColorPicker,
    ElContainer,
    ElDialog,
    ElDivider,
    ElDropdown,
    ElDropdownItem,
    ElDropdownMenu,
    ElForm,
    ElFormItem,
    ElHeader,
    ElInput,
    ElInputNumber,
    ElMain,
    ElMenu,
    ElMenuItem,
    ElOption,
    ElPopconfirm,
    ElPopover,
    ElRadioButton,
    ElRadioGroup,
    ElRow,
    ElSelect,
    ElSlider,
    ElSwitch,
    ElTable,
    ElTableColumn,
    ElTabPane,
    ElTabs,
    ElTag,
    ElText,
    ElTooltip,
    ElTree,
  })) {
    if (!app.component(name)) app.component(name, component as Component);
  }
  const components = {
    NativeFileUpload: FileField,
    NativeImageUpload: (props: Record<string, unknown>) =>
      h(FileField, { ...props, image: true }),
    NativeImagesUpload: (props: Record<string, unknown>) =>
      h(FileField, { ...props, image: true, multiple: true }),
    NativeUserSelect: UserSelect,
    NativeDeptSelect: DeptSelect,
    NativeDictSelect: DictSelect,
    NativeApiSelect: ApiSelect,
    NativeRichText: RichTextarea,
  };
  for (const [name, component] of Object.entries(components)) {
    app.component(name, component);
    formCreate.component(name, component);
    FcDesigner.formCreate.component(name, component);
  }
  installed.add(app);
}
