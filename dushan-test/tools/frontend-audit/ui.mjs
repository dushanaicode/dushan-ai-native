export function controls(page, assert) {
  const main = () => page.locator('#__vben_main_content');
  const dialog = () => page.getByRole('dialog').last();
  const exact = (text) =>
    new RegExp(`${text.replaceAll(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`)}$`);
  async function responseDuring(path, method, operation) {
    const [response] = await Promise.all([
      page.waitForResponse(
        async (response) =>
          new URL(response.url()).pathname === path &&
          response.request().method() === method &&
          (await response.json()).code !== 1_004_003,
        { timeout: 15_000 },
      ),
      operation(),
    ]);
    const body = await response.json();
    assert.equal(body.code, 0, JSON.stringify({ path, body }));
    return body.data;
  }
  return {
    main,
    dialog,
    responseDuring,
    async fill(label, value, scope = dialog()) {
      await scope.getByLabel(exact(label)).fill(String(value));
      await scope.getByLabel(exact(label)).press('Tab');
    },
    async select(label, option, scope = dialog()) {
      await scope.getByRole('combobox', { name: exact(label) }).press('Enter');
      await page.getByRole('option', { name: option, exact: true }).click();
    },
    async toggle(label, checked, scope = dialog()) {
      const input = scope.getByRole('switch', { name: exact(label) });
      if ((await input.isChecked()) !== checked)
        await input.locator('..').click();
    },
    async create(button, endpoint, fill) {
      await main().getByRole('button', { name: button, exact: true }).click();
      await dialog().waitFor();
      await fill();
      const id = await responseDuring(`${endpoint}/create`, 'POST', () =>
        dialog()
          .getByRole('button', { name: /^(确认|保存)$/ })
          .last()
          .click(),
      );
      await dialog().waitFor({ state: 'hidden' });
      return id;
    },
    rows(id) {
      return main().locator(`tr[rowid="${id}"]`);
    },
    async rowButton(id, name) {
      await main()
        .locator(`tr[rowid="${id}"]`)
        .getByRole('button', { name, exact: true })
        .last()
        .click();
    },
    async close() {
      await dialog().locator('button[data-slot="dialog-close"]').click();
    },
    async search(label, value) {
      await main()
        .getByRole('textbox', { name: exact(label) })
        .fill(value);
      await main().getByRole('button', { name: '搜索', exact: true }).click();
    },
    async confirm() {
      await page
        .getByRole('button', { name: /^(确定|确认)$/ })
        .last()
        .click();
    },
  };
}
