import type { Ref } from 'vue';

import type { VbenFormSchema } from '@vben/common-ui';

import type { AuthApi } from '#/api/core/auth';

import { computed, nextTick, onMounted, ref } from 'vue';

import { z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { getLoginTenantsApi } from '#/api/core/auth';
import { takeErrorMessage } from '#/api/error-feedback';
import { useTenantStore } from '#/store/tenant';

interface LoginForm {
  getFormApi: () => { setFieldValue: (name: string, value: string) => void };
}

export function useLoginTenant(form: Ref<LoginForm | undefined>) {
  const store = useTenantStore();
  const config = ref<AuthApi.TenantConfig>();
  const tenantLoading = ref(true);
  const tenantError = ref('');
  const enabled = import.meta.env.VITE_APP_TENANT_ENABLE === 'true';
  const selectTenant = computed(() => enabled && config.value?.enabled);

  async function loadTenants() {
    tenantLoading.value = true;
    tenantError.value = '';
    config.value = undefined;
    try {
      config.value = await getLoginTenantsApi();
    } catch (error) {
      tenantError.value = takeErrorMessage(error, $t('tenantLogin.loadFailed'));
      tenantLoading.value = false;
      return;
    }
    if (!config.value.enabled) {
      tenantLoading.value = false;
      return;
    }
    if (!enabled) {
      tenantError.value = $t('tenantLogin.configuration');
      tenantLoading.value = false;
      return;
    }
    if (config.value.tenants.length === 0) {
      tenantError.value = $t('tenantLogin.empty');
      tenantLoading.value = false;
      return;
    }
    const selected =
      config.value.tenants.find((item) => item.id === store.lastTenantId) ??
      (config.value.tenants.length === 1 ? config.value.tenants[0] : undefined);
    store.lastTenantId = selected?.id ?? null;
    await nextTick();
    form.value?.getFormApi().setFieldValue('tenantId', selected?.id ?? '');
    await nextTick();
    tenantLoading.value = false;
  }

  const tenantFields = computed(() => {
    const settings = config.value;
    if (!selectTenant.value || !settings) return [];
    return [
      {
        component: 'VbenSelect',
        componentProps: {
          options: settings.tenants.map((item) => ({
            label: item.name,
            value: item.id,
          })),
          placeholder: $t('tenantLogin.select'),
        },
        dependencies: {
          triggerFields: ['tenantId'],
          resolve({ values }) {
            store.lastTenantId = values.tenantId;
            return {};
          },
        },
        fieldName: 'tenantId',
        label: $t('tenantLogin.tenant'),
        rules: z.string().min(1, { message: $t('tenantLogin.select') }),
      } satisfies VbenFormSchema,
    ];
  });

  onMounted(loadTenants);
  return {
    loadTenants,
    selectTenant,
    tenantError,
    tenantFields,
    tenantLoading,
  };
}
