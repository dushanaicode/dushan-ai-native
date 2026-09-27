<script setup lang="ts">
import { UserSelectFormField } from '#/components';
import { createUserSelectPorts } from '#/services/user-select/ports';
defineOptions({ name: 'NativeUserSelect', inheritAttrs: false });
const ports = createUserSelectPorts();
</script>

<template>
  <UserSelectFormField v-bind="$attrs" :ports="ports" />
</template>
