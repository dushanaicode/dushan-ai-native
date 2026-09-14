import type { CSSProperties, MaybeRefOrGetter, VNode } from 'vue';

import type { DescriptionsProps } from '@vben/common-ui';

export type DescriptionData = Record<string, unknown>;
export interface DescriptionItemSchema {
  field?: string;
  label: string | VNode;
  content?: ((data: DescriptionData) => unknown) | string | VNode;
  hidden?: ((data: DescriptionData) => boolean) | boolean;
  contentStyle?: CSSProperties;
  labelStyle?: CSSProperties;
  span?: number;
}
export interface DescriptionsOptions {
  data?: MaybeRefOrGetter<DescriptionData | undefined>;
  schema?: DescriptionItemSchema[];
  componentProps?: DescriptionsProps;
}
