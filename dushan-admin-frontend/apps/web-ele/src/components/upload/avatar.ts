import type { VCropper } from '@vben/common-ui';

import type { FilePorts } from './files';

import { parseStoredFile, validateFile } from './files';

export async function uploadCroppedAvatar(options: {
  cropper: Pick<InstanceType<typeof VCropper>, 'getCropImage'>;
  ports: Pick<FilePorts, 'upload'>;
  maxSize: number;
  signal: AbortSignal;
}) {
  const { signal } = options;
  signal.throwIfAborted();
  const blob = await options.cropper.getCropImage(
    'image/png',
    0.92,
    'blob',
    240,
    240,
  );
  signal.throwIfAborted();
  if (!(blob instanceof Blob) || blob.size === 0)
    throw new Error('裁剪器没有生成有效图片');
  const file = new File([blob], 'avatar.png', { type: 'image/png' });
  validateFile(file, {
    accept: 'image/png',
    maxSize: options.maxSize,
    maxNumber: 1,
  });
  const result = await options.ports.upload(file, {
    signal,
    onProgress: () => undefined,
  });
  signal.throwIfAborted();
  return parseStoredFile(result);
}
