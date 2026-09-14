import type { CSSProperties } from 'vue';

import type { TagStyle } from '../services/dictionary/types';

import { isValidColor, TinyColor } from '@vben/utils';

export type TagVariant = 'light' | 'outline' | 'pastel' | 'solid';

export const tagColors: Record<string, string> = {
  primary: '#409eff',
  danger: '#f56c6c',
  info: '#909399',
  success: '#67c23a',
  warning: '#e6a23c',
  default: '#d9d9d9',
  error: '#ff4d4f',
  processing: '#1677ff',
  blue: '#1677ff',
  cyan: '#13c2c2',
  green: '#52c41a',
  orange: '#fa8c16',
  pink: '#eb2f96',
  purple: '#722ed1',
  red: '#f5222d',
  yellow: '#fadb14',
};

export function tagPresentation(
  style: null | TagStyle,
  colorType: string,
  variant: TagVariant,
): CSSProperties {
  const color = style?.color || tagColors[colorType] || colorType;
  if (!isValidColor(color)) throw new TypeError(`标签颜色无效：${color}`);
  const base = new TinyColor(color);
  const text = style?.textColor;
  const foreground = text || (base.isLight() ? '#1f2937' : '#fff');
  if (text && !isValidColor(text))
    throw new TypeError(`标签文字颜色无效：${text}`);
  if (style) {
    switch (style.variant) {
      case 'link':
      case 'text': {
        return {
          backgroundColor: 'transparent',
          borderColor: 'transparent',
          color: text || base.toHexString(),
        };
      }
      case 'outline': {
        return {
          backgroundColor: 'transparent',
          borderColor: base.toHexString(),
          color: text || base.toHexString(),
        };
      }
      case 'solid': {
        return {
          backgroundColor: base.toHexString(),
          borderColor: 'transparent',
          color: foreground,
        };
      }
    }
  }
  switch (variant) {
    case 'solid': {
      return {
        backgroundColor: base.toHexString(),
        borderColor: 'transparent',
        color: foreground,
      };
    }
    case 'outline': {
      return {
        backgroundColor: 'transparent',
        borderColor: base.toHexString(),
        color: base.toHexString(),
      };
    }
    case 'pastel': {
      return {
        backgroundColor: base.clone().setAlpha(0.3).toRgbString(),
        borderColor: 'transparent',
        color: base.darken(20).toHexString(),
      };
    }
    case 'light': {
      return {
        backgroundColor: base.clone().setAlpha(0.15).toRgbString(),
        borderColor: 'transparent',
        color: base.toHexString(),
      };
    }
  }
}
