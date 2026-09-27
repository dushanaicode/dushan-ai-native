export interface DataSourceUrlProps {
  dbType?: string;
  modelValue?: string;
}

export interface DataSourceUrlConfig {
  database: string;
  dbType: string;
  host: string;
  password: string;
  port: number | undefined;
  query: string;
  username: string;
}
