import type { FilePorts } from '#/components';

import { uploadFile } from '#/api/infra/file';

/**
 * 文件上传端口。
 *
 * 后端 `POST /infra/file/upload` 直接返回访问 URL，业务 VO 的头像、Logo
 * 等字段均保存该 URL（如 `avatar: HttpUrl`）。因此端口的文件 id 即 URL：
 * `upload` 包装响应为满足 StoredFile 契约的记录，`resolve` 将 id 原样
 * 解析回可访问地址，与 `CropperAvatar`/`FileUpload`/`ImageUpload` 配合。
 */
const EXTENSION_MIME: Record<string, string> = {
  avif: 'image/avif',
  gif: 'image/gif',
  jpeg: 'image/jpeg',
  jpg: 'image/jpeg',
  mp4: 'video/mp4',
  pdf: 'application/pdf',
  png: 'image/png',
  svg: 'image/svg+xml',
  webp: 'image/webp',
  zip: 'application/zip',
};

function fileName(url: string): string {
  try {
    const path = new URL(url, window.location.origin).pathname;
    const name = path.split('/').pop();
    return name || url;
  } catch {
    return url;
  }
}

function mediaType(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() ?? '';
  return EXTENSION_MIME[ext] ?? 'application/octet-stream';
}

export function createFilePorts(options?: {
  configId?: string;
  directory?: string;
}): FilePorts {
  return {
    upload: async (file) => {
      const url = await uploadFile(file, options?.directory, options?.configId);
      return {
        id: url,
        mediaType: file.type || mediaType(file.name),
        name: file.name,
        size: file.size,
      };
    },
    resolve: async (ids) => {
      return ids.map((id) => {
        const name = fileName(id);
        return {
          id,
          mediaType: mediaType(name),
          name,
          size: 0,
          url: id,
        };
      });
    },
  };
}
