/** 检查未通过，由 CLI 统一展示诊断并返回非零退出码。 */
export class CheckError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CheckError';
  }
}
