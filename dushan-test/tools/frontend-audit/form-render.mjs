import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runFormRender({
  page,
  goto,
  test,
  assert,
  settle,
  output,
}) {
  const ui = controls(page, assert);
  const entries = [
    ['/system/user', '新增用户'],
    ['/system/role', '新增角色'],
    ['/system/menu', '新增菜单'],
    ['/system/dept', '新增部门'],
    ['/system/post', '新增岗位'],
    ['/system/dict', '新增字典类型'],
    ['/system/notification/notice', '新增通知'],
    ['/system/announcement', '新增公告'],
    ['/system/message/mail/account', '新增邮箱账号'],
    ['/system/message/mail/template', '新增邮件模板'],
    ['/system/message/sms/channel', '新增短信渠道'],
    ['/system/message/sms/template', '新增短信模板'],
    ['/system/tenant-manage/tenant', '新增租户'],
    ['/system/tenant-manage/tenantPackage', '新增租户套餐'],
    ['/system/oauth2/client', '新增OAuth2 客户端'],
    ['/system/social/client', '新增社交客户端'],
    ['/infra/config', '新增配置类型'],
    ['/infra/file/config', '新增文件配置'],
    ['/infra/job', '新增任务'],
    ['/infra/mq', '新增消息定义'],
    ['/infra/dataSourceConfig', '新增数据源'],
  ];
  for (const [index, [path, button]] of entries.entries()) {
    await test(
      `${button}：表单渲染、必填校验与取消`,
      async () => {
        await goto(path);
        await ui
          .main()
          .getByRole('button', { name: button, exact: true })
          .click();
        await ui.dialog().waitFor();
        await settle();
        await writeFile(
          join(output, `${index + 1}-form.txt`),
          await ui.dialog().ariaSnapshot(),
        );
        await ui
          .dialog()
          .getByRole('button', { name: /^(确认|保存)$/ })
          .last()
          .click();
        await settle();
        assert(await ui.dialog().isVisible(), '空表单被提交或关闭');
        const content = await ui.dialog().innerText();
        assert(
          /请输入|请选择|不能为空|必填|Invalid|至少/.test(content),
          '没有出现必填字段提示',
        );
        await ui
          .dialog()
          .getByRole('button', { name: '取消', exact: true })
          .click();
        await ui.dialog().waitFor({ state: 'hidden' });
      },
      { allowedCodes: [422] },
    );
  }
}
