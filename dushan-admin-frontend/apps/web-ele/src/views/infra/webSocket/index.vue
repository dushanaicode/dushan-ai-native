<script lang="ts" setup>
import { Page } from '@vben/common-ui';

import ControlPanel from './components/control-panel.vue';
import ReceiveMessage from './components/receive-message.vue';
import SendMessage from './components/send-message.vue';
import { useWebSocketTest } from './composables/use-websocket-test';

defineOptions({ name: 'InfraWebSocket' });

const websocketTest = useWebSocketTest();
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert
        title="WebSocket 实时通信"
        url="https://doc.iocoder.cn/websocket/"
      />
    </template>

    <div
      class="grid h-full min-h-0 grid-cols-1 gap-4 overflow-hidden xl:grid-cols-[360px_minmax(0,1fr)_minmax(0,1fr)]"
    >
      <ControlPanel :context="websocketTest" />
      <SendMessage :context="websocketTest" />
      <ReceiveMessage :context="websocketTest" />
    </div>
  </Page>
</template>
