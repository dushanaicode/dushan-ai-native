/** 生成 128 位随机标识；getRandomValues 在局域网 HTTP 页面也可用。 */
export function createRandomId(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}
