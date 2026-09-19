export interface DataSourceUrlProps {
  modelValue?: string;
}

export type DbDriverMode = 'async' | 'sync';

export interface DbTypeConfig {
  asyncDriver: string;
  defaultPort: number;
  name: string;
  syncDriver: string;
}

export interface DataSourceUrlConfig {
  database: string;
  dbType: string;
  filePath?: string;
  host: string;
  password: string;
  port: number;
  schema: string;
  useAsync: boolean;
  username: string;
}
