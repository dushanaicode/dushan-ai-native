import type { DescriptionsOptions } from './types';

import { defineComponent, h, shallowReactive } from 'vue';

import Description from './description.vue';

export function useDescription(options: DescriptionsOptions) {
  const state = shallowReactive({ ...options });
  const api = {
    getState: () => state,
    setState: (value: Partial<DescriptionsOptions>) =>
      Object.assign(state, value),
  };
  const Component = defineComponent({
    name: 'DescriptionView',
    setup:
      (_, { attrs, slots }) =>
      () =>
        h(Description, { ...state, ...attrs }, slots),
  });
  return [Component, api] as const;
}
