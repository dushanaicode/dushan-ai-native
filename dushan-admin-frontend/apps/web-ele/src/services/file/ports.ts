import type { InfraFileApi } from '#/api/infra/file';
import type { FilePorts } from '#/components';

import { uploadBusinessFile } from '#/api/infra/file';

import { resolveFileUrl } from './file-access';

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

export function createFilePorts(
  usage: InfraFileApi.FileUploadUsage,
): FilePorts {
  return {
    upload: async (file, { signal }) => {
      const url = await uploadBusinessFile(file, usage, signal);
      return {
        id: url,
        mediaType: file.type || mediaType(file.name),
        name: file.name,
        size: file.size,
      };
    },
    resolve: async (ids, signal) => {
      return Promise.all(
        ids.map(async (id) => {
          const name = fileName(id);
          return {
            id,
            mediaType: mediaType(name),
            name,
            size: 0,
            url: await resolveFileUrl(id, signal),
          };
        }),
      );
    },
  };
}
