export const SwitchStatus = {
  DISABLED: 0,
  ENABLED: 1,
} as const;

export type SwitchStatusValue =
  (typeof SwitchStatus)[keyof typeof SwitchStatus];

export const statusSwitchProps = {
  activeValue: SwitchStatus.ENABLED,
  inactiveValue: SwitchStatus.DISABLED,
} as const;
