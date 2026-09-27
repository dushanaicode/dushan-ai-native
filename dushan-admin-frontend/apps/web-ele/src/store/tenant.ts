import { defineStore } from 'pinia';

export const useTenantStore = defineStore('tenant', {
  persist: { pick: ['lastTenantId'] },
  state: (): {
    currentTenantId: null | string;
    lastTenantId: null | string;
  } => ({
    currentTenantId: null,
    lastTenantId: null,
  }),
});
