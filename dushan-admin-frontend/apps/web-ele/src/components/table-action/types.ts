import type { ButtonProps } from 'element-plus';

export interface ActionItem extends Omit<Partial<ButtonProps>, 'color'> {
  auth?: string[];
  color?: 'error' | 'success' | 'warning';
  danger?: boolean;
  divider?: boolean;
  icon?: string;
  ifShow?: ((action: ActionItem) => boolean) | boolean;
  label?: string;
  onClick?: () => Promise<void> | void;
  popConfirm?: {
    title: string;
    confirm: () => Promise<void> | void;
    cancel?: () => void;
    disabled?: boolean;
    okText?: string;
    cancelText?: string;
  };
  tooltip?: string;
}

export function canShowAction(
  action: ActionItem,
  hasAccess: (codes: string[]) => boolean,
) {
  return (
    (!action.auth?.length || hasAccess(action.auth)) &&
    (typeof action.ifShow === 'function'
      ? action.ifShow(action)
      : action.ifShow !== false)
  );
}
