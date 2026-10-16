export interface FieldMeta {
  name: string
  alias: string
  role: 'dimension' | 'measure' | 'normal'
  dataType: string
  filterable: boolean
  isDate: boolean
  isOrg: boolean
  unit?: string | null
  dictSetId?: number | null
  dictSetName?: string | null
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface DataModel {
  id: string
  code: string
  name: string
  module: string
  owner: string
  description?: string
  status: string
  table: string
  sourceType?: 'table' | 'report'
  sourceSql?: string | null
  sourceRef?: string | null
  sourceTemplate?: string | null
  bizDateType?: 'balance' | 'period' | null
  bizDateField?: string | null
  bizDateStartParam?: string | null
  bizDateEndParam?: string | null
  createdAt: string
  fields: FieldMeta[]
}

export interface ReportInfo {
  reptid: string
  reptna: string
  repttp: string
  fieldCount: number
  bizDateType: 'balance' | 'period' | null
  imported: boolean
}

export interface ReportBizDate {
  type: 'balance' | 'period' | 'none' | null
  field: string | null
  start_param: string | null
  end_param: string | null
}

export interface ReportPreviewField {
  field_name: string
  alias: string
  role: 'dimension' | 'measure'
  data_type: string
  is_date: boolean
}

export interface ReportPreviewColumn {
  name: string
  dataType: string
}

export interface ReportPreviewResult {
  reptid: string
  sqlText: string
  templateSql: string
  columns: ReportPreviewColumn[]
  bizDate: ReportBizDate | null
  fields: ReportPreviewField[]
}

export interface ResolvePreviewResult {
  sqlText: string
  templateSql: string
}

export interface BatchImportSuccessItem {
  reptid: string
  reptna: string
  modelId: string
}

export interface BatchImportFailedItem {
  reptid: string
  reptna: string
  error: string
}

export interface BatchImportResult {
  success: BatchImportSuccessItem[]
  failed: BatchImportFailedItem[]
}

export interface IndicatorMeasure {
  fieldName: string
  alias: string
  aggFunc: string
  modelId?: string  // 字段来源模型：缺省 = 主模型；与 config.joins 中的 modelId 对应
  unit?: string
  displayPrecision?: number
  derivatives?: string[]
}

export interface IndicatorConfig {
  modelId: string
  indicatorType?: 'basic' | 'derived'
  dimensions: { fieldName: string; alias: string; modelId?: string }[]
  measures?: IndicatorMeasure[]
  measure?: IndicatorMeasure
  filters?: Array<{ fieldName: string; alias?: string; modelId?: string; operator: string; value?: string; joinWith?: string }>
  outputFields?: Array<{ fieldName: string; alias: string; role: 'dimension' | 'measure'; aggFunc?: string }>
  joins?: Array<{ modelId: string; joinType: string; conditions: Array<{ leftField: string; rightField: string }> }>
  baseIndicatorIds?: string[]
  derived?: { operator: 'copy' | 'sum' | 'difference' | 'ratio'; alias: string }
  basic?: { bizCaliber?: string; techCaliber?: string; visibility?: string; expireType?: string; expireDate?: string }
  schedule?: { frequency?: string; resultTable?: string; priority?: number; runTime?: string }
}

export interface Indicator {
  id: string
  code: string
  name: string
  modelId: string
  parentId: string
  categoryId: string
  status: string
  favorite: boolean
  config: IndicatorConfig
  sqlText: string
  createdAt: string
  updatedAt: string
}

export interface IndicatorTreeNode {
  id: string
  label: string
  code?: string
  categoryName?: string
  kind?: 'folder' | 'indicator'
  indicatorId?: string
  children: IndicatorTreeNode[]
}

export interface IndicatorCategory {
  id: string
  name: string
  parentId: string
  sortOrder: number
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface ResultTable {
  id: string
  table_name: string
  comment: string
  frequency: string
  bound: boolean
  schemaName?: string
  dimensionCapacity?: number
  physicalStatus?: string
  lastCheckedAt?: string | null
  lastCheckMessage?: string
  created_at: string
}

export interface Schedule {
  id: string
  indicator_id: string
  indicator_name?: string
  indicator_code?: string
  name: string
  frequency: string
  run_time: string
  enabled: boolean
  last_run_at?: string | null
  next_run_at?: string | null
  dateOption?: Record<string, unknown> | null
  scope?: string
  categoryId?: string
}

export interface ModelOption {
  id: string
  code: string
  name: string
  table: string
  module: string
  fields: FieldMeta[]
  bizDateType?: 'balance' | 'period' | null
}

export interface IndicatorOption {
  id: string
  code: string
  name: string
  modelId: string
  categoryId: string
  status: string
  favorite: boolean
  parentId: string
  resultTable: string
  createdAt: string
  updatedAt: string
}

export interface BootstrapData {
  models: ModelOption[]
  indicators: IndicatorOption[]
  indicatorCategories: IndicatorCategory[]
  schedules: Schedule[]
  jobs: Record<string, unknown>[]
}

export interface DictCategory {
  id: number
  categoryCode: string
  categoryName: string
  sort: number
  remark: string
  setCount: number
  createdAt: string
}

export interface DictSet {
  id: number
  categoryId: number
  categoryCode: string
  categoryName: string
  setCode: string
  setName: string
  status: string
  remark: string
  itemCount: number
  refCount: number
  createdAt: string
}

export interface DictItem {
  id: number
  setId: number
  setCode: string
  setName: string
  itemCode: string
  itemName: string
  sort: number
  status: string
  createdAt: string
}
