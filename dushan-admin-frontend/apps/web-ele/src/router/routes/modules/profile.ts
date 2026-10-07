import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'Profile',
    path: '/profile',
    component: () => import('#/views/_core/profile/index.vue'),
    meta: {
      icon: 'lucide:user',
      hideInMenu: true,
      title: $t('page.auth.profile'),
    },
  },
  {
    name: 'MyNoticeMessage',
    path: '/my-notice-message',
    component: () =>
      import('#/views/system/notification/notice-message/index.vue'),
    meta: {
      icon: 'ep:message',
      hideInMenu: true,
      title: $t('utils.notification.myMessages'),
    },
  },
];

export default routes;
