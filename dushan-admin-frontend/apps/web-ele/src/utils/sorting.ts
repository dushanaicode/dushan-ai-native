export interface TableSort {
  field: string;
  order: 'asc' | 'desc' | null;
}

export function toSortingFields(sorts: TableSort[]) {
  return sorts.flatMap(({ field, order }) =>
    order === null ? [] : [{ field, order }],
  );
}
