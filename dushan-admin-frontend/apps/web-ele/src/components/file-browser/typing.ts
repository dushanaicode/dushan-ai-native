import type { InfraFileApi } from '#/api/infra/file';
import type { InfraFileConfigApi } from '#/api/infra/file-config';

export type FileObject = InfraFileApi.FileObjectVO;

export type ListObjectsResp = InfraFileApi.FileListObjectsRespVO;

export type FileConfigSimple = InfraFileConfigApi.FileConfigSimpleRespVO;

export interface BreadcrumbItem {
  name: string;
  prefix: string;
}

export type ViewMode = 'grid' | 'list';

export const STORAGE_LABEL_MAP: Record<number, string> = {
  1: '数据库',
  10: '本地',
  11: 'FTP',
  12: 'SFTP',
  20: 'S3',
};

export function getStorageLabel(storage?: number) {
  if (storage === undefined || storage === null) {
    return '';
  }
  return STORAGE_LABEL_MAP[storage] || `类型 ${storage}`;
}

export interface FileBrowserProps {
  height?: string;
}

export interface FileBrowserEmits {
  (e: 'openFile', item: FileObject): void;
}

export function isImageType(type?: null | string) {
  return Boolean(type?.startsWith('image/'));
}

export function getFileIcon(item: FileObject) {
  if (item.isDirectory) {
    return 'lucide:folder';
  }

  const type = item.type || '';
  if (type.includes('image')) {
    return 'lucide:file-image';
  }
  if (type.includes('pdf')) {
    return 'lucide:file-text';
  }
  if (type.includes('video')) {
    return 'lucide:file-video';
  }
  if (type.includes('audio')) {
    return 'lucide:file-audio';
  }
  if (
    type.includes('zip') ||
    type.includes('rar') ||
    type.includes('compressed')
  ) {
    return 'lucide:file-archive';
  }
  return 'lucide:file';
}

export type PreviewType = 'audio' | 'image' | 'none' | 'pdf' | 'text' | 'video';

export function getPreviewType(type?: null | string): PreviewType {
  if (!type) {
    return 'none';
  }
  if (type.startsWith('image/')) {
    return 'image';
  }
  if (type.startsWith('video/')) {
    return 'video';
  }
  if (type.startsWith('audio/')) {
    return 'audio';
  }
  if (type === 'application/pdf') {
    return 'pdf';
  }
  if (
    type.startsWith('text/') ||
    type.includes('json') ||
    type.includes('xml') ||
    type.includes('javascript') ||
    type.includes('yaml') ||
    type.includes('csv')
  ) {
    return 'text';
  }
  return 'none';
}
