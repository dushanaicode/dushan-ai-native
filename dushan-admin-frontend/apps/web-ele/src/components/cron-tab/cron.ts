export const cronFields = [
  { key: 'minute', min: 0, max: 59 },
  { key: 'hour', min: 0, max: 23 },
  { key: 'day', min: 1, max: 31 },
  { key: 'month', min: 1, max: 12 },
  { key: 'week', min: 0, max: 6 },
] as const;

export type CronField =
  | { mode: 'every' }
  | { mode: 'list'; values: number[] }
  | { mode: 'range'; start: number; end: number }
  | { mode: 'step'; start: '*' | number; step: number };
export type CronMode = CronField['mode'];

export function newCronField(mode: CronMode, index: number): CronField {
  const { min, max } = cronFields[index] as (typeof cronFields)[number];
  switch (mode) {
    case 'every': {
      return { mode };
    }
    case 'range': {
      return { mode, start: min, end: max };
    }
    case 'step': {
      return { mode, start: '*', step: 1 };
    }
    case 'list': {
      return { mode, values: [min] };
    }
  }
}

function parseField(text: string, index: number): CronField {
  const { min, max } = cronFields[index] as (typeof cronFields)[number];
  const number = (value: string) => {
    if (!/^\d+$/.test(value)) throw new TypeError('cron字段必须是整数');
    const parsed = Number(value);
    if (!Number.isSafeInteger(parsed) || parsed < min || parsed > max)
      throw new RangeError('cron字段超出范围');
    return parsed;
  };
  if (text === '*') return { mode: 'every' };
  const range = /^(\d+)-(\d+)$/.exec(text);
  if (range) {
    const start = number(range[1] as string);
    const end = number(range[2] as string);
    if (start > end) throw new RangeError('cron范围顺序无效');
    return { mode: 'range', start, end };
  }
  const interval = /^(\*|\d+)\/(\d+)$/.exec(text);
  if (interval) {
    const step = Number(interval[2]);
    if (!Number.isSafeInteger(step) || step < 1 || step > max - min + 1)
      throw new RangeError('cron步长无效');
    return {
      mode: 'step',
      start: interval[1] === '*' ? '*' : number(interval[1] as string),
      step,
    };
  }
  return {
    mode: 'list',
    values: text.split(',').map((value) => number(value)),
  };
}

export function parseCron(expression: string): CronField[] {
  const parts = expression.trim().split(/\s+/);
  if (parts.length !== cronFields.length)
    throw new TypeError('cron生成器只接受五段表达式');
  return parts.map((part, index) => parseField(part, index));
}

function formatField(field: CronField): string {
  switch (field.mode) {
    case 'every': {
      return '*';
    }
    case 'range': {
      return `${field.start}-${field.end}`;
    }
    case 'step': {
      return `${field.start}/${field.step}`;
    }
    case 'list': {
      return field.values.join(',');
    }
  }
}

export function generateCron(fields: CronField[]) {
  const expression = fields.map((field) => formatField(field)).join(' ');
  // 生成器的输入来自可编辑表单，越界或空选择不能悄悄改成任意值。
  parseCron(expression);
  return expression;
}
