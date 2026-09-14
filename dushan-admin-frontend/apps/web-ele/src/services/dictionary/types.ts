export interface TagStyle {
  color: string;
  textColor: string;
  variant: 'link' | 'outline' | 'solid' | 'text';
}

export interface DictionaryEntry {
  colorType?: null | string;
  dictType: string;
  label: string;
  permission?: null | string;
  tagStyle?: null | TagStyle;
  value: string;
}

export type DictionaryValue = boolean | number | string;
export type DictionaryValueType = 'boolean' | 'number' | 'string';
