import type { DatePickerProps } from 'element-plus';

import { $t } from '@vben/locales';

import dayjs from 'dayjs';

export function getRangePickerDefaultProps(): Partial<DatePickerProps> {
  const range = (start: dayjs.Dayjs, end: dayjs.Dayjs): [Date, Date] => [
    start.toDate(),
    end.toDate(),
  ];
  const periods = [
    ['today', () => range(dayjs().startOf('day'), dayjs().endOf('day'))],
    [
      'yesterday',
      () => {
        const yesterday = dayjs().subtract(1, 'day');
        return range(yesterday.startOf('day'), yesterday.endOf('day'));
      },
    ],
    [
      'last7Days',
      () => range(dayjs().subtract(6, 'day').startOf('day'), dayjs()),
    ],
    [
      'last30Days',
      () => range(dayjs().subtract(29, 'day').startOf('day'), dayjs()),
    ],
    ['thisWeek', () => range(dayjs().startOf('week'), dayjs())],
    [
      'lastWeek',
      () => {
        const lastWeek = dayjs().subtract(1, 'week');
        return range(lastWeek.startOf('week'), lastWeek.endOf('week'));
      },
    ],
    ['thisMonth', () => range(dayjs().startOf('month'), dayjs())],
    [
      'lastMonth',
      () => {
        const lastMonth = dayjs().subtract(1, 'month');
        return range(lastMonth.startOf('month'), lastMonth.endOf('month'));
      },
    ],
  ] as const;
  return {
    defaultTime: [new Date(2000, 0, 1), new Date(2000, 0, 1, 23, 59, 59)],
    endPlaceholder: $t('utils.rangePicker.endTime'),
    format: 'YYYY-MM-DD HH:mm:ss',
    rangeSeparator: $t('utils.rangePicker.separator'),
    shortcuts: periods.map(([key, value]) => ({
      text: $t(`utils.rangePicker.${key}`),
      value,
    })),
    startPlaceholder: $t('utils.rangePicker.beginTime'),
  };
}
