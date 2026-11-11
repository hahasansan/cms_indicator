<template>
  <div class="page" >
    <div class="page-head">
      <div><h1>{{ editingId ? '编辑指标' : '新增指标' }}</h1><div class="desc">配置指标的业务口径和加工规则。</div></div>
      <div class="actions"><el-button type="button" @click="emit('back')">返回指标管理</el-button><el-button type="primary" :disabled="saving" @click="save">保存指标</el-button></div>
    </div>

    <el-card shadow="never" class="compact-builder">
      <div class="compact-builder-body">
        <div class="builder-section-title">
          <div><h2>指标基本信息</h2></div>
        </div>
        <el-form label-position="left" label-width="120px" class="basic-form-grid">
          <el-form-item label="指标名称" required class="basic-span-2"><el-input v-model="name" placeholder="例如：各机构资金余额" /></el-form-item>
          <el-form-item label="指标类型"><el-select v-model="indicatorType"><el-option value="basic" label="基础指标" /><el-option value="derived" label="衍生指标" /></el-select></el-form-item>
          <el-form-item label="所属分类"><el-tree-select v-model="categoryId" :data="categoryTreeForSelect" check-strictly :render-after-expand="false" /></el-form-item>
          <el-form-item v-if="filterConfigAvailable" label="数据模型" class="basic-span-2"><el-select v-model="modelId" filterable :filter-method="filterModel" placeholder="选择或输入名称筛选"><el-option v-for="modelItem in filteredModels" :key="modelItem.id" :value="modelItem.id" :label="`${modelItem.name}（${modelItem.table}）`" /></el-select></el-form-item>
          <el-form-item v-if="filterConfigAvailable" label="业务时间类型" required>
            <el-select v-model="bizDateType" placeholder="请选择">
              <el-option value="balance" label="余额类（单日）" />
              <el-option value="period" label="时段类（区间）" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="filterConfigAvailable" label="业务时间字段" required class="basic-span-2">
            <el-select v-model="bizDateField" placeholder="选择日期型字段" :disabled="!bizDateType" filterable>
              <el-option v-for="field in bizDateFields" :key="field.name" :value="field.name" :label="`${field.alias}（${field.name}）`" />
            </el-select>
          </el-form-item>
          <el-form-item label="业务口径" class="basic-span-all"><el-input v-model="bizCaliber" type="textarea" :rows="2" placeholder="用业务语言描述指标的计算口径" /></el-form-item>
        </el-form>
        <div v-if="filterConfigAvailable" class="builder-config-grid">
          <section class="builder-section">
            <div class="section-title-line"><h3>维度字段</h3><span class="muted">用于分组展示</span></div>
            <div class="check-list field-check-list">
              <el-checkbox-group v-model="dimensionKeys">
                <el-checkbox v-for="field in dimensionFields" :key="`${field.modelId}:${field.name}`" :value="dimKey(field.modelId, field.name)" class="builder-check-row">
                  <span>{{ field.alias }}<small class="muted">{{ field.name }} · {{ field.dataType }} · {{ field.source === 'main' ? '主模型' : field.source + ' ' + field.modelName }}</small></span>
                </el-checkbox>
              </el-checkbox-group>
            </div>
            <div v-if="!dimensionFields.length" class="empty compact-empty">当前模型没有维度字段</div>
          </section>

          <section class="builder-section measure-section">
            <div class="section-title-line"><div><h3>度量字段</h3><p class="section-help">可直接选择模型度量字段，或用公式计算；两种方式都可选择统计方式。</p></div><div><el-button size="small" @click="refreshMeasureFunctions">刷新公式</el-button><el-button size="small" @click="addMeasure">添加度量</el-button></div></div>
            <div v-for="(measure, index) in measures" :key="index" class="measure-config-row">
              <el-radio-group :model-value="measure.sourceType || (measure.functionId ? 'formula' : 'field')" size="small" @change="(source: string | number | boolean) => setMeasureSource(measure, source === 'formula' ? 'formula' : 'field')">
                <el-radio-button label="field">模型字段</el-radio-button>
                <el-radio-button label="formula">公式计算</el-radio-button>
              </el-radio-group>
              <el-select
                v-if="(measure.sourceType || (measure.functionId ? 'formula' : 'field')) === 'field'"
                v-model="measure.fieldName"
                placeholder="选择模型度量字段"
                @change="(fieldName: string) => onMeasureFieldChange(measure, fieldName)"
              >
                <el-option v-for="field in measureFields" :key="`${field.modelId}:${field.name}`" :value="field.name" :label="`${field.alias}（${field.name}）`" />
              </el-select>
              <el-select v-else v-model="measure.functionId" placeholder="选择公式" @change="(id: string) => onMeasureFunctionChange(measure, id)">
                <el-option v-for="formula in measureFunctions" :key="formula.id" :value="formula.id" :label="`${formula.name}（${formula.parameterCount} 个操作数）`" />
              </el-select>
              <el-input v-model="measure.alias" placeholder="结果名称，例如：资金余额" />
              <el-button type="danger" link @click="removeMeasure(index)">×</el-button>
              <div class="measure-aggregation">
                <span>统计方式</span>
                <el-select v-model="measure.aggFunc" placeholder="选择统计方式">
                  <el-option value="SUM" label="SUM 求和" />
                  <el-option value="AVG" label="AVG 平均值" />
                  <el-option value="MAX" label="MAX 最大值" />
                  <el-option value="MIN" label="MIN 最小值" />
                  <el-option value="COUNT" label="COUNT 计数" />
                  <el-option value="NONE" label="不聚合" />
                </el-select>
              </div>
              <div class="measure-aggregation">
                <span>小数位数</span>
                <el-input-number
                  v-model="measure.displayPrecision"
                  :min="0"
                  :max="10"
                  :step="1"
                  controls-position="right"
                  size="small"
                  placeholder="不限制"
                />
              </div>
              <div v-if="isFormulaMeasure(measure) && measure.functionId && activeFormulaFunction(measure)" class="formula-inputs">
                <div class="formula-overview">
                  <div class="formula-line"><span class="formula-label">公式模板</span><code>{{ activeFormula(measure) }}</code></div>
                  <div v-if="activeFormulaFunction(measure)?.description" class="formula-description">{{ activeFormulaFunction(measure)?.description }}</div>
                  <div class="formula-line"><span class="formula-label">代入结果</span><code>{{ formulaWithInputs(measure) }}</code></div>
                </div>
                <div class="formula-operands">
                  <div v-for="(input, inputIndex) in measure.inputs || []" :key="inputIndex" class="formula-operand-row">
                    <span class="operand-token">{{ '{' + (inputIndex + 1) + '}' }}</span>
                    <span class="operand-meaning">{{ formulaParamName(measure, inputIndex) || '未维护含义' }}</span>
                    <el-select v-model="input.fieldName" :placeholder="operandPlaceholder(measure, inputIndex)">
                      <el-option v-for="field in formulaFields" :key="`${field.modelId}:${field.name}`" :value="field.name" :label="`${field.alias}（${field.name}）`" />
                    </el-select>
                    <small class="operand-selected">{{ selectedOperandField(input) }}</small>
                  </div>
                </div>
                <div v-if="formulaMissingParamNames(measure)" class="formula-tip">
                  该公式尚未维护操作数含义，建议前往<el-button link type="primary" @click="openFunctionManagement">度量公式管理</el-button>补充，业务人员才能看懂每个字段代表什么。
                </div>
              </div>
              <div v-else-if="!isFormulaMeasure(measure) && !measure.functionId" class="formula-inputs muted">
                {{ measureFunctions.length ? '请选择公式。' : '请先在“度量公式管理”中创建公式。' }}
              </div>
              <div v-else-if="!isFormulaMeasure(measure)" class="formula-inputs muted">
                {{ measureFields.length ? '选择模型中的度量字段作为计算来源。' : '当前模型没有可用的度量字段。' }}
              </div>
              <div v-if="canConfigureDerivatives" class="measure-derivatives-summary">
                <span class="measure-derivatives-text">
                  衍生度量：<b>{{ measure.derivatives?.length ? `${measure.derivatives.length} 项已选` : '未配置' }}</b>
                  <small class="muted">可选，与基础度量绑定并随指标一起生成</small>
                </span>
                <el-button size="small" @click="openDerivativeDialog(index)">衍生度量配置</el-button>
              </div>
              <div v-if="needsBizDays(measure) && !bizDateType" class="formula-system-note warning">
                ⚠️ 该公式使用了 <code>{__BIZ_DAYS__}</code> 系统占位符，需先在上方「业务时间」配置业务日期类型和字段
              </div>
              <div v-else-if="needsBizDays(measure) && bizDateType" class="formula-system-note">
                💡 <code>{__BIZ_DAYS__}</code> 将按 {{ bizDateType === 'period' ? '时段区间天数' : '1（余额类单日值不变）' }} 计算
              </div>
            </div>
            <div v-if="!measures.length" class="empty compact-empty">请点击“添加度量”，选择公式并绑定公式字段。</div>
            <div class="measure-example"><b>公式示例：</b><span><strong>{1} * {2}</strong> 可计算数量乘单价，再选择 SUM 求和</span><span><strong>{1} / NULLIF({2}, 0)</strong> 可计算多列比率，再选择所需统计方式</span><span><strong>{1} / NULLIF({__BIZ_DAYS__}, 0)</strong> 可计算区间日均，{__BIZ_DAYS__} 为系统内置的业务区间天数</span></div>
            <div v-if="!measureFunctions.length" class="measure-example"><el-button link type="primary" @click="openFunctionManagement">前往度量公式管理</el-button></div>
          </section>
        </div>

        <div v-if="filterConfigAvailable" class="builder-config-grid">
          <section class="builder-section">
            <div class="section-title-line"><h3>筛选条件</h3><el-button size="small" @click="addFilter">添加条件</el-button></div>
            <div v-for="(filter, index) in filters" :key="index" class="filter-config-row">
              <el-select v-if="index" v-model="filter.joinWith"><el-option value="AND" label="AND" /><el-option value="OR" label="OR" /></el-select>
              <span v-else class="filter-first">当</span>
              <el-select v-model="filter.fieldName" filterable placeholder="输入中文名或字段名搜索" @change="(val: string) => onFilterFieldChange(filter, val)">
                <el-option-group label="维度">
                  <el-option v-for="field in dimensionFields" :key="`dim-${field.modelId}:${field.name}`" :value="field.name" :label="`${field.alias}（${field.name}）`" />
                </el-option-group>
                <el-option-group label="度量">
                  <el-option v-for="field in measureFields" :key="`mes-${field.modelId}:${field.name}`" :value="field.name" :label="`${field.alias}（${field.name}）`" />
                </el-option-group>
              </el-select>
              <el-select v-model="filter.operator" :disabled="isFilterDictBound(filter)">
                <el-option v-for="op in ['=','!=','>','>=','<','<=','LIKE','IN']" :key="op" :value="op" :label="op" />
              </el-select>
              <!-- 字段关联了码值集：码值多选下拉（展示业务名称，底层存 itemCode） -->
              <el-select
                v-if="isFilterDictBound(filter)"
                :model-value="(filter.value || '').split(',').filter(Boolean)"
                multiple filterable collapse-tags
                placeholder="选择码值（业务名称）"
                style="min-width: 240px"
                @update:model-value="(val: string[]) => onFilterDictChange(filter, val)"
              >
                <el-option
                  v-for="item in (filterDictItemsMap[getFilterSetId(filter) || -1] || [])"
                  :key="item.itemCode"
                  :value="item.itemCode"
                  :label="item.itemName"
                />
              </el-select>
              <!-- 普通字段：手工输入 -->
              <el-input v-else v-model="filter.value" placeholder="条件值" />
              <el-button type="danger" link @click="filters.splice(index, 1)">×</el-button>
            </div>
            <div v-if="!filters.length" class="empty compact-empty">暂无筛选条件</div>
          </section>

        </div>

        <div v-if="indicatorType === 'derived'" class="builder-section derived-compact">
          <div class="section-title-line"><h3>衍生规则</h3><span class="muted">选择基础指标后生成组合指标</span></div>
          <el-form label-width="100px">
            <el-form-item label="计算方式"><el-select v-model="derivedOperator" style="width:100%"><el-option value="copy" label="复用（1 个基础指标）" /><el-option value="sum" label="求和（2 个基础指标 A+B）" /><el-option value="difference" label="差值（2 个基础指标 A-B）" /><el-option value="ratio" label="比率（2 个基础指标 A÷B）" /></el-select></el-form-item>
            <el-form-item label="基础指标 A"><el-select v-model="baseIndicatorIds[0]" style="width:100%" placeholder="请选择"><el-option value="" label="请选择" /><el-option v-for="item in candidateIndicators" :key="item.id" :value="item.id" :label="item.name" /></el-select></el-form-item>
            <el-form-item v-if="derivedOperator !== 'copy'" label="基础指标 B"><el-select v-model="baseIndicatorIds[1]" style="width:100%" placeholder="请选择"><el-option value="" label="请选择" /><el-option v-for="item in candidateIndicators.filter((candidate) => candidate.id !== baseIndicatorIds[0])" :key="item.id" :value="item.id" :label="item.name" /></el-select></el-form-item>
          </el-form>
          <div class="measure-example"><b>提示：</b><span>维度与度量来自基础指标 A，要求 B 与 A 维度一致；FULL OUTER JOIN 后按维度合并。</span></div>
        </div>

        <section class="builder-section trial-section" ref="trialResultRef">
          <div class="section-title-line"><h3>试算</h3>
            <div class="trial-actions">
              <template v-if="filterConfigAvailable && bizDateType">
                <span class="trial-date-label">业务日期：</span>
                <el-form-item v-if="bizDateType === 'balance'" label-width="0" class="trial-date-item">
                  <el-date-picker v-model="trialBizDate" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" placeholder="选择业务日期" />
                </el-form-item>
                <template v-else>
                  <el-form-item label-width="0" class="trial-date-item">
                    <el-date-picker v-model="trialBizStart" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" placeholder="起" />
                  </el-form-item>
                  <el-form-item label-width="0" class="trial-date-item">
                    <el-date-picker v-model="trialBizEnd" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" placeholder="止" />
                  </el-form-item>
                </template>
              </template>
              <el-button size="small" type="primary" :loading="loading" :disabled="filterConfigAvailable && bizDateType && !trialDateReady" @click="trial">试算</el-button>
            </div>
          </div>
          <div v-if="trialError" class="trial-error">试算失败：{{ trialError }}</div>
          <div v-if="trialDone && trialRows.length" class="trial-result">
            <div class="trial-result-title">试算结果（前 {{ trialRows.length }} 行）</div>
            <el-table :data="trialRows" size="small" border stripe max-height="360">
              <el-table-column v-for="key in trialKeys" :key="key" :prop="key" :label="key" min-width="120" show-overflow-tooltip />
            </el-table>
          </div>
          <div v-else-if="trialDone && !trialRows.length && !trialError" class="trial-empty">试算完成，未返回数据</div>
          <div v-else class="trial-hint">点击"试算"执行 SQL 并查看前 10 行结果。</div>
        </section>

        <section v-if="showSqlPreview" class="builder-section sql-preview-section">
          <div class="section-title-line"><h3>SQL 预览</h3><el-button size="small" :loading="loading" @click="preview">生成 SQL</el-button></div>
          <pre class="sql">{{ sqlText || '点击"生成 SQL"查看系统将执行的 SQL' }}</pre>
        </section>

        <div class="compact-builder-footer"><span class="muted">已配置 {{ dimensions.length }} 个维度、{{ measures.length }} 个度量、{{ filters.length }} 个条件</span><el-button size="small" @click="toggleSqlPreview">{{ showSqlPreview ? '隐藏 SQL 预览' : '显示 SQL 预览' }}</el-button></div>
      </div>
    </el-card>

    <el-dialog v-model="derivativeDialogOpen" :title="derivativeDialogTitle" width="640px" append-to-body>
      <div class="derivative-dialog">
        <div class="derivative-dialog-tip">衍生度量会与当前基础度量绑定，并随指标一起生成；不配置则只生成基础度量。</div>
        <section class="derivative-block">
          <div class="derivative-block-head"><b>业务日期衍生</b><small>运行时按所选业务日期参数查询余额快照；较上日按自然日计算。</small></div>
          <el-checkbox-group v-model="derivativeDraft" class="derivative-check-group">
            <el-checkbox v-for="option in timeDerivatives" :key="option.value" :value="option.value">{{ option.label }}</el-checkbox>
          </el-checkbox-group>
        </section>
        <section class="derivative-block">
          <div class="derivative-block-head"><b>统计衍生</b><small>按自然月、季、年对基础度量做累计、均值或首末值计算。</small></div>
          <el-checkbox-group v-model="derivativeDraft" class="derivative-check-group">
            <el-checkbox v-for="option in statisticalDerivatives" :key="option.value" :value="option.value">{{ option.label }}</el-checkbox>
          </el-checkbox-group>
        </section>
      </div>
      <template #footer>
        <el-button @click="derivativeDraft = []">清空</el-button>
        <el-button @click="derivativeDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="confirmDerivativeDialog">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onMounted, ref, watch } from 'vue'
import { api, jsonBody } from '../../api'
import type { BootstrapData, DataModel, DictItem, Indicator, IndicatorConfig, IndicatorMeasure, MeasureFunction } from '../../types'

type IndicatorKind = NonNullable<IndicatorConfig['indicatorType']>
type Filter = NonNullable<IndicatorConfig['filters']>[number]
const props = defineProps<{ data: BootstrapData; editingId?: string }>()
const emit = defineEmits<{ saved: [id: string]; back: [] }>()
const notify = inject<(message: string) => void>('notify', () => undefined)
const editing = computed(() => props.data.indicators.find((item) => item.id === props.editingId))
// editingDetail：通过 GET /api/indicators/{id} 拉取的完整 Indicator（含 config/sqlText）
const editingDetail = ref<Indicator | null>(null)
// modelDetail：通过 GET /api/models/{id} 拉取的完整 DataModel（含 fields）
const modelDetail = ref<DataModel | null>(null)
// baseIndicatorDetails：衍生指标基础指标 id -> 完整 Indicator 缓存（IndicatorOption 无 config）
const baseIndicatorDetails = ref<Record<string, Indicator>>({})
const name = ref(editing.value?.name || '')
const indicatorType = ref<IndicatorKind>('basic')
const modelId = ref(editing.value?.modelId || props.data.models[0]?.id || '')
const categoryId = ref(editing.value?.categoryId || props.data.indicatorCategories.find((item) => item.id !== 'root' && item.enabled)?.id || 'root')
const bizCaliber = ref('')
const bizDateType = ref<'' | 'balance' | 'period'>('')
const bizDateField = ref('')
type DimItem = Exclude<IndicatorConfig['dimensions'], undefined>[number]
const dimKey = (modelId?: string, fieldName?: string) => `${modelId || ''}:${fieldName || ''}`
const dimensionKeys = ref<string[]>([])
const dimStore = ref<Map<string, DimItem>>(new Map())
const dimensions = computed<IndicatorConfig['dimensions']>(() => dimensionKeys.value.map((key) => {
  const stored = dimStore.value.get(key)
  if (stored) return stored
  const [mid, fname] = key.split(':', 2)
  const found = dimensionFields.value.find((f) => (f.modelId || '') === mid && f.name === fname)
  return { fieldName: found?.name || fname, alias: found?.alias || fname, modelId: mid || '' }
}).filter((item) => item.fieldName))
const measures = ref<IndicatorMeasure[]>([])
const measureFunctions = ref<MeasureFunction[]>([])
const measureFunctionById = computed(() => Object.fromEntries(measureFunctions.value.map((formula) => [formula.id, formula])))
async function refreshMeasureFunctions() {
  try {
    measureFunctions.value = await api<MeasureFunction[]>('/api/measure-functions')
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}
onMounted(refreshMeasureFunctions)
const filters = ref<Filter[]>([])
const baseIndicatorIds = ref<string[]>(['', ''])
const derivedOperator = ref<NonNullable<NonNullable<IndicatorConfig['derived']>['operator']>>('copy')
watch(derivedOperator, (op) => {
  if (op === 'copy') {
    baseIndicatorIds.value = [baseIndicatorIds.value[0] || '']
    while (baseIndicatorIds.value.length < 2) baseIndicatorIds.value.push('')
  }
}, { immediate: false })
const candidateIndicators = computed(() => props.data.indicators.filter((candidate) => candidate.id !== props.editingId))
const resultTable = ref(editing.value?.resultTable || '')
const scheduleFrequency = ref('日')

// 异步加载编辑中指标的完整详情（含 config），拿到后同步表单字段
async function loadEditingDetail(id?: string) {
  if (!id) { editingDetail.value = null; return }
  try {
    editingDetail.value = await api<Indicator>(`/api/indicators/${id}`)
    syncFormFromDetail()
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}
// 异步加载主模型完整详情（含 fields），ModelOption.fields 是空数组
async function loadModelDetail(id?: string) {
  if (!id || !props.data.models.find((m) => m.id === id)) { modelDetail.value = null; return }
  try {
    modelDetail.value = await api<DataModel>(`/api/models/${id}`)
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}
// 异步加载衍生基础指标完整详情（含 config）
async function loadBaseIndicatorDetail(id?: string) {
  if (!id || baseIndicatorDetails.value[id]) return
  try {
    const detail = await api<Indicator>(`/api/indicators/${id}`)
    baseIndicatorDetails.value = { ...baseIndicatorDetails.value, [id]: detail }
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}

// 从 editingDetail.value 同步所有 config 相关表单字段（编辑场景初始化）
function syncFormFromDetail() {
  const detail = editingDetail.value
  if (!detail) return
  const cfg = detail.config
  if (cfg.indicatorType) indicatorType.value = cfg.indicatorType
  bizCaliber.value = cfg.basic?.bizCaliber || ''
  bizDateType.value = cfg.bizDate?.type || ''
  bizDateField.value = cfg.bizDate?.field || ''
  const initialDims = cfg.dimensions?.map((item) => ({ fieldName: item.fieldName, alias: item.alias, modelId: item.modelId })) || []
  dimensionKeys.value = initialDims.map((item) => dimKey(item.modelId, item.fieldName))
  dimStore.value = new Map(initialDims.map((item) => [dimKey(item.modelId, item.fieldName), item as DimItem]))
  measures.value = getMeasures(detail)
  filters.value = cfg.filters?.map((item) => ({ ...item })) || []
  baseIndicatorIds.value = (cfg.baseIndicatorIds || []).slice(0, 2)
  while (baseIndicatorIds.value.length < 2) baseIndicatorIds.value.push('')
  derivedOperator.value = cfg.derived?.operator || 'copy'
  if (cfg.schedule?.resultTable) resultTable.value = cfg.schedule.resultTable
  scheduleFrequency.value = cfg.schedule?.frequency || '日'
}
const sqlText = ref('')
const showSqlPreview = ref(false)
const loading = ref(false)
const saving = ref(false)
const trialRows = ref<Record<string, unknown>[]>([])
const trialKeys = computed(() => trialRows.value.length ? Object.keys(trialRows.value[0]) : [])
const trialError = ref('')
const trialDone = ref(false)
const trialResultRef = ref<HTMLElement | null>(null)
// 试算用业务日期
const trialBizDate = ref('')
const trialBizStart = ref('')
const trialBizEnd = ref('')
const trialDateReady = computed(() => {
  if (!bizDateType.value) return true
  if (bizDateType.value === 'balance') return !!trialBizDate.value
  return !!trialBizStart.value && !!trialBizEnd.value
})
watch(bizDateType, () => { trialBizDate.value = ''; trialBizStart.value = ''; trialBizEnd.value = '' })

const model = computed(() => modelDetail.value)
// 数据模型下拉筛选：按名称/表名"以输入文字开头"匹配
const modelQuery = ref('')
const filteredModels = computed(() => {
  const q = modelQuery.value.trim().toLowerCase()
  if (!q) return props.data.models
  return props.data.models.filter((m) => (m.name || '').toLowerCase().startsWith(q) || (m.table || '').toLowerCase().startsWith(q))
})
const filterModel = (query: string) => { modelQuery.value = query }
type FieldWithSource = { name: string; alias: string; dataType?: string; modelId: string; modelName: string; source: 'main' | `j${number}`; dictSetId?: number | null; isDate?: boolean }
const dimensionFields = computed<FieldWithSource[]>(() => {
  const main = model.value
  if (!main) return []
  return main.fields.filter((field) => field.role === 'dimension').map((field) => ({
    name: field.name, alias: field.alias, dataType: field.dataType,
    modelId: main.id, modelName: main.name, source: 'main' as const, dictSetId: field.dictSetId ?? null, isDate: field.isDate,
  }))
})
const canConfigureDerivatives = computed(() => {
  const sourceType = model.value?.sourceType
  return (sourceType === 'report' || sourceType === 'custom_sql') && bizDateType.value === 'balance' && !!model.value?.sourceTemplate
})
const bizDateFields = computed(() => (model.value?.fields || []).filter((field) => field.isDate))
function applyModelBizDateDefaults(detail: DataModel) {
  bizDateType.value = detail.bizDateType || ''
  bizDateField.value = detail.bizDateField || ''
}
const measureFields = computed<FieldWithSource[]>(() => {
  const main = model.value
  if (!main) return []
  return main.fields.filter((field) => field.role === 'measure').map((field) => ({
    name: field.name, alias: field.alias, dataType: field.dataType,
    modelId: main.id, modelName: main.name, source: 'main' as const, dictSetId: field.dictSetId ?? null,
  }))
})
const formulaFields = computed<FieldWithSource[]>(() => {
  const main = model.value
  if (!main) return []
  return main.fields.map((field) => ({
    name: field.name,
    alias: field.alias,
    dataType: field.dataType,
    modelId: main.id,
    modelName: main.name,
    source: 'main' as const,
    dictSetId: field.dictSetId ?? null,
    isDate: field.isDate,
  }))
})
const filterConfigAvailable = computed(() => indicatorType.value === 'basic')
const timeDerivatives = [
  { value: 'prev_day_value', label: '较上日值' },
  { value: 'prev_day_growth', label: '较上日增幅(%)' },
  { value: 'prev_month_value', label: '较上月值' },
  { value: 'prev_month_growth', label: '较上月增幅(%)' },
  { value: 'year_start_comparison_value', label: '较年初值' },
  { value: 'year_start_comparison_growth', label: '较年初增幅(%)' },
  { value: 'prev_year_value', label: '较去年同期值' },
  { value: 'prev_year_growth', label: '较去年同期增幅(%)' },
]
const statisticalDerivatives = [
  { value: 'month_cumulative', label: '月累计' },
  { value: 'quarter_cumulative', label: '季累计' },
  { value: 'year_cumulative', label: '年累计' },
  { value: 'month_average', label: '月均值' },
  { value: 'quarter_average', label: '季均值' },
  { value: 'year_average', label: '年均值' },
  { value: 'month_start_value', label: '月初值' },
  { value: 'quarter_start_value', label: '季初值' },
  { value: 'year_start_value', label: '年初值' },
  { value: 'month_end_value', label: '月末值' },
  { value: 'quarter_end_value', label: '季末值' },
  { value: 'year_end_value', label: '年末值' },
]

// ===================== 衍生度量弹窗 =====================
const derivativeDialogOpen = ref(false)
const derivativeDialogIndex = ref(-1)
const derivativeDraft = ref<string[]>([])
const derivativeDialogTitle = computed(() => {
  const measure = measures.value[derivativeDialogIndex.value]
  const alias = measure?.alias?.trim()
  return alias ? `衍生度量配置 · ${alias}` : '衍生度量配置'
})
function openDerivativeDialog(index: number) {
  derivativeDialogIndex.value = index
  derivativeDraft.value = [...(measures.value[index]?.derivatives || [])]
  derivativeDialogOpen.value = true
}
function confirmDerivativeDialog() {
  const measure = measures.value[derivativeDialogIndex.value]
  if (measure) measure.derivatives = [...derivativeDraft.value]
  derivativeDialogOpen.value = false
}

// ===================== 公式操作数含义 =====================
const isFormulaMeasure = (measure: IndicatorMeasure) =>
  (measure.sourceType || (measure.functionId ? 'formula' : 'field')) === 'formula'
const activeFormulaFunction = (measure: IndicatorMeasure): MeasureFunction | undefined =>
  measure.functionId ? measureFunctionById.value[measure.functionId] : undefined
const activeFormula = (measure: IndicatorMeasure) =>
  measure.formula || activeFormulaFunction(measure)?.formula || ''
// 操作数含义按 {1}、{2}… 顺序对应到公式参数列表
const formulaParamName = (measure: IndicatorMeasure, index: number) =>
  (activeFormulaFunction(measure)?.parameters || [])[index] || ''
function operandPlaceholder(measure: IndicatorMeasure, index: number) {
  const meaning = formulaParamName(measure, index)
  return meaning ? `选择代表「${meaning}」的字段` : `选择第 ${index + 1} 个操作数对应的字段`
}
function findOperandField(input: { fieldName: string; modelId?: string }) {
  return formulaFields.value.find((field) => field.name === input.fieldName && (!input.modelId || field.modelId === input.modelId))
}
const selectedOperandField = (input: { fieldName: string; modelId?: string }) => {
  const field = findOperandField(input)
  return field ? `已选：${field.alias}` : '未选择字段'
}
// 把占位符替换为已选字段的业务名称，直观展示公式最终含义
function formulaWithInputs(measure: IndicatorMeasure) {
  const formula = activeFormula(measure)
  if (!formula) return ''
  return formula.replace(/\{(\d+)\}/g, (token, number: string) => {
    const input = measure.inputs?.[Number(number) - 1]
    if (!input?.fieldName) return token
    return findOperandField(input)?.alias || input.fieldName
  })
}
function formulaMissingParamNames(measure: IndicatorMeasure) {
  const count = measure.inputs?.length || 0
  const parameters = activeFormulaFunction(measure)?.parameters || []
  return count > 0 && Array.from({ length: count }, (_, index) => parameters[index] || '').every((name) => !name)
}
function needsBizDays(measure: IndicatorMeasure): boolean {
  const formula = activeFormula(measure)
  return /\{__BIZ_DAYS__\}/.test(formula)
}

function onMeasureFunctionChange(measure: IndicatorMeasure, functionId: string) {
  const formula = measureFunctionById.value[functionId]
  if (!formula) return
  measure.functionId = formula.id
  measure.sourceType = 'formula'
  measure.formula = formula.formula
  measure.fieldName = ''
  measure.aggFunc = 'NONE'
  measure.inputs = Array.from({ length: formula.parameterCount }, () => ({ fieldName: '', modelId: modelId.value }))
  if (!measure.alias) measure.alias = formula.name
}
function setMeasureSource(measure: IndicatorMeasure, source: 'field' | 'formula') {
  measure.sourceType = source
  measure.fieldName = ''
  measure.modelId = modelId.value
  measure.functionId = ''
  measure.formula = ''
  measure.inputs = []
  measure.aggFunc = 'SUM'
  if (source === 'formula') return
}
function onMeasureFieldChange(measure: IndicatorMeasure, fieldName: string) {
  const field = measureFields.value.find((item) => item.name === fieldName)
  if (!field) return
  measure.sourceType = 'field'
  measure.modelId = field.modelId
  if (!measure.alias) measure.alias = field.alias
}
function onFilterFieldChange(filter: Filter, fieldName: string) {
  const field = [...dimensionFields.value, ...measureFields.value].find((f) => f.name === fieldName)
  if (!field) return
  filter.modelId = field.modelId
  filter.alias = field.alias
  // 切换字段后重置条件值
  filter.value = ''
  if (field.dictSetId) {
    // 关联了码值集：操作符锁定为 IN，拉取码值项
    filter.operator = 'IN'
    ensureFilterDictItems(field.dictSetId)
  } else {
    // 普通字段：操作符恢复为 =
    filter.operator = '='
  }
}

// ===================== 条件筛选码值多选支持 =====================
// 按 setId 缓存码值项（仅 enabled）
const filterDictItemsMap = ref<Record<number, DictItem[]>>({})
// 拉取过的 setId 集合，避免重复请求
const filterDictLoadedSet = new Set<number>()

/** 根据当前 filter 字段查找关联的 dictSetId */
function getFilterSetId(filter: Filter): number | null {
  const field = [...dimensionFields.value, ...measureFields.value].find((f) => f.name === filter.fieldName)
  return field?.dictSetId ?? null
}

/** 判断 filter 字段是否关联了码值集 */
function isFilterDictBound(filter: Filter): boolean {
  return getFilterSetId(filter) !== null
}

/** 拉取指定 setId 的码值项（仅 enabled），带缓存 */
async function ensureFilterDictItems(setId: number) {
  if (filterDictLoadedSet.has(setId)) return
  filterDictLoadedSet.add(setId)
  try {
    const items = await api<DictItem[]>(`/api/dict/items?setId=${setId}&onlyEnabled=1`)
    filterDictItemsMap.value = { ...filterDictItemsMap.value, [setId]: items }
  } catch (e) {
    filterDictLoadedSet.delete(setId)
    notify(e instanceof Error ? e.message : String(e))
  }
}

/** 码值多选 change：把选中的 itemCode 数组用逗号 join 存入 filter.value */
function onFilterDictChange(filter: Filter, val: string[]) {
  filter.value = val.join(',')
}
const enabledCategories = computed(() => props.data.indicatorCategories.filter((item) => item.enabled))
// 所属分类下拉：按层级结构展示分类树
type CategoryOption = { value: string; label: string; children: CategoryOption[] }
const categoryTreeForSelect = computed<CategoryOption[]>(() => {
  const cats = props.data.indicatorCategories
  const nodes = new Map(cats.map((c) => [c.id, { value: c.id, label: c.name, children: [] as CategoryOption[] }]))
  const roots: CategoryOption[] = []
  cats.forEach((c) => {
    const node = nodes.get(c.id)!
    const parent = c.parentId && c.parentId !== 'root' ? nodes.get(c.parentId) : undefined
    if (parent) parent.children.push(node)
    else roots.push(node)
  })
  return roots
})

watch(() => props.editingId, (id) => { loadEditingDetail(id) }, { immediate: true })
watch(modelId, (id) => { loadModelDetail(id) }, { immediate: true })
// 主模型详情加载后：新增场景自动回填维度/度量；编辑场景预加载码值项
watch(modelDetail, (detail, oldDetail) => {
  if (!detail) {
    dimensionKeys.value = []
    dimStore.value = new Map()
    measures.value = []
    if (!editing.value) {
      filters.value = []
      bizDateType.value = ''
      bizDateField.value = ''
    }
    return
  }
  // 业务时间参数默认取模型：新增指标、切换模型、或老指标尚未保存该配置时回填
  if (
    (oldDetail && oldDetail.id !== detail.id)
    || !editing.value
    || (!bizDateType.value && !bizDateField.value)
  ) {
    applyModelBizDateDefaults(detail)
  }
  if (editing.value) {
    // 编辑场景：模型详情就绪后，对关联了码值集的筛选条件预加载码值项
    for (const filter of filters.value) {
      const setId = getFilterSetId(filter)
      if (setId) ensureFilterDictItems(setId)
    }
    return
  }
  // 新增场景：模型切换时清空旧维度/度量，回填新模型默认维度
  const autoDims = dimensionFields.value.slice(0, 3)
  dimensionKeys.value = autoDims.map((f) => dimKey(f.modelId, f.name))
  for (const f of autoDims) dimStore.value.set(dimKey(f.modelId, f.name), { fieldName: f.name, alias: f.alias, modelId: f.modelId })
  measures.value = defaultMeasures()
  filters.value = []
})
// 衍生基础指标详情按需拉取（baseIndicatorIds 变化时）
watch(baseIndicatorIds, (ids) => {
  for (const id of ids) if (id) loadBaseIndicatorDetail(id)
}, { immediate: true, deep: true })
watch(dimensionKeys, (keys) => {
  // 去重 + 将新加入的字段按默认别名写入 store，避免下次 compute 时丢失
  const seen = new Set<string>()
  const deduped: string[] = []
  for (const k of keys) {
    if (!k || seen.has(k)) continue
    seen.add(k)
    deduped.push(k)
    if (!dimStore.value.has(k)) {
      const [mid, fname] = k.split(':', 2)
      const found = dimensionFields.value.find((f) => (f.modelId || '') === mid && f.name === fname)
      dimStore.value.set(k, { fieldName: found?.name || fname, alias: found?.alias || fname, modelId: mid || '' })
    }
  }
  if (deduped.length !== keys.length) dimensionKeys.value = deduped
}, { immediate: true })
watch(() => props.data.models, () => { if (!measures.value.length) measures.value = defaultMeasures() }, { immediate: true })
watch(measureFunctions, (functions) => {
  if (functions.length && modelDetail.value && !editing.value && !measures.value.length) {
    measures.value = defaultMeasures()
  }
})

function getMeasures(indicator: Indicator): IndicatorMeasure[] {
  const configured = indicator.config.measures ?? (indicator.config.measure ? [indicator.config.measure] : [])
  return configured.map((measure) => ({
    ...measure,
    sourceType: measure.sourceType || (measure.functionId ? 'formula' : 'field'),
    aggFunc: measure.aggFunc || (measure.functionId ? 'NONE' : 'SUM'),
    inputs: measure.inputs?.map((item) => ({ ...item })) || [],
    derivatives: measure.derivatives || [],
  }))
}
function defaultMeasures(): IndicatorMeasure[] {
  const field = measureFields.value[0]
  if (field) {
    return [{
      fieldName: field.name,
      modelId: field.modelId,
      aggFunc: 'SUM',
      sourceType: 'field',
      alias: field.alias,
      functionId: '',
      formula: '',
      inputs: [],
      derivatives: [],
    }]
  }
  const formula = measureFunctions.value[0]
  return formula ? [{
    fieldName: '',
    aggFunc: 'NONE',
    sourceType: 'formula',
    functionId: formula.id,
    formula: formula.formula,
    inputs: Array.from({ length: formula.parameterCount }, () => ({ fieldName: '', modelId: modelId.value })),
    alias: formula.name,
    derivatives: [],
  }] : []
}
function addMeasure() { measures.value.push({ fieldName: '', aggFunc: 'SUM', alias: '', functionId: '', formula: '', inputs: [], derivatives: [] }) }
function removeMeasure(index: number) { measures.value.splice(index, 1) }
function openFunctionManagement() {
  window.open('/indicator-center/functions', '_blank', 'noopener')
}
function addFilter() {
  const field = model.value?.fields[0]
  if (!field) return
  const hasDict = !!field.dictSetId
  if (hasDict) ensureFilterDictItems(field.dictSetId!)
  filters.value.push({ fieldName: field.name, alias: field.alias, operator: hasDict ? 'IN' : '=', value: '', joinWith: 'AND' })
}
function dedupDims(list: IndicatorConfig['dimensions']): IndicatorConfig['dimensions'] {
  const seen = new Set<string>()
  const result = (list || []).filter((item) => {
    const k = `${item.modelId || ''}:${item.fieldName}`
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
  return result
}
function collect(): IndicatorConfig {
  const config = { modelId: modelId.value, indicatorType: indicatorType.value, dimensions: dedupDims(dimensions.value.map((dim) => ({ fieldName: dim.fieldName, alias: dim.alias, modelId: dim.modelId }))), measures: measures.value.map((m) => ({ ...m, displayPrecision: m.displayPrecision ?? undefined, derivatives: m.derivatives || [], modelId: m.modelId })), filters: filters.value, baseIndicatorIds: baseIndicatorIds.value.filter((id) => id), derived: { operator: derivedOperator.value as 'copy' | 'sum' | 'difference' | 'ratio', alias: name.value || '衍生指标值' }, basic: { bizCaliber: bizCaliber.value }, bizDate: { type: bizDateType.value, field: bizDateField.value }, schedule: { frequency: scheduleFrequency.value, resultTable: resultTable.value } }
  return config
}
async function preview() { loading.value = true; try { const result = await api<{ sqlText: string }>('/api/sql/previews', { method: 'POST', body: jsonBody({ config: collect() }) }); sqlText.value = result.sqlText } catch (error) { notify(error instanceof Error ? error.message : String(error)) } finally { loading.value = false } }
async function trial() {
  loading.value = true; trialDone.value = false; trialError.value = ''
  try {
    const config = collect()
    const dateOption = buildTrialDateOption()
    const result = await api<{ sqlText: string; rows: Record<string, unknown>[] }>('/api/sql/trials', { method: 'POST', body: jsonBody({ config, dateOption }) })
    trialRows.value = result.rows
  } catch (error) {
    trialRows.value = []
    trialError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
    trialDone.value = true
    nextTick(() => trialResultRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
}
function buildTrialDateOption(): Record<string, unknown> | undefined {
  if (!bizDateType.value) return undefined
  if (bizDateType.value === 'balance' && trialBizDate.value) {
    return { type: 'balance', single: { option: 'specific', value: trialBizDate.value } }
  }
  if (bizDateType.value === 'period' && trialBizStart.value && trialBizEnd.value) {
    return {
      type: 'period',
      start: { option: 'specific', value: trialBizStart.value },
      end: { option: 'specific', value: trialBizEnd.value },
    }
  }
  return undefined
}
function toggleSqlPreview() { showSqlPreview.value = !showSqlPreview.value }
async function save() {
  if (!name.value.trim()) { notify('请填写指标名称'); return }
  if (!modelId.value && indicatorType.value === 'basic') { notify('请选择数据模型'); return }
  if (indicatorType.value === 'basic' && bizDateType.value) {
    if (!bizDateField.value) { notify('请选择业务时间字段'); return }
  }
  if (indicatorType.value === 'basic' && measures.value.some((measure) => measure.derivatives?.length) && !canConfigureDerivatives.value) {
    notify('衍生度量仅适用于配置了业务日期参数的余额类指标')
    return
  }
  if (indicatorType.value === 'basic' && measures.value.some((measure) => (
    measure.sourceType === 'formula'
      ? !measure.functionId || !measure.alias.trim() || !measure.inputs?.length || measure.inputs.some((input) => !input.fieldName)
      : !measure.fieldName
  ))) {
    notify('请为每个度量选择模型字段，或选择公式并绑定公式字段')
    return
  }
  if (indicatorType.value === 'derived') {
    if (!baseIndicatorIds.value[0]) { notify('请选择基础指标 A'); return }
    if (derivedOperator.value !== 'copy' && !baseIndicatorIds.value[1]) { notify('请选择基础指标 B'); return }
  }
  saving.value = true
  try {
    const body = jsonBody({ name: name.value, modelId: modelId.value, categoryId: categoryId.value, status: editing.value?.status || 'draft', config: collect() })

    const path = props.editingId ? `/api/indicators/${props.editingId}` : '/api/indicators'
    const result = await api<Indicator>(path, { method: props.editingId ? 'PUT' : 'POST', body })
    notify('指标已保存')
    emit('saved', result.id)
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  } finally {
    saving.value = false
  }
}

</script>

<style scoped>
.page {
  max-width: 100%;
  margin: 0;
  width: 100%;
}

.compact-builder-body {
  width: 100%;
  padding: 24px;
  display: grid;
  gap: 18px;
}

.builder-section-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.builder-section-title h2 {
  margin: 0;
  color: var(--ink);
  font-size: 18px;
}

.builder-section-title p {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.basic-meta {
  font-size: 12px;
  text-align: right;
}

.basic-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px 24px;
}

.basic-form-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.basic-form-grid :deep(.el-form-item__content) {
  min-width: 0;
}

.basic-form-grid :deep(.el-input),
.basic-form-grid :deep(.el-select),
.basic-form-grid :deep(.el-tree-select) {
  width: 100%;
}

.basic-span-2 {
  grid-column: span 2;
}

.basic-span-all {
  grid-column: 1 / -1;
}

.builder-config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
}

.builder-section {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--line-soft);
  border-radius: 7px;
  background: #fbfdff;
}

.section-title-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.section-title-line h3 {
  margin: 0;
  color: var(--ink);
  font-size: 14px;
}

.field-check-list {
  max-height: 260px;
  overflow: auto;
}

.check-list {
  border: 1px solid var(--line);
  border-radius: 7px;
  max-height: 360px;
  overflow: auto;
  background: white;
}

.measure-config-row,
.filter-config-row {
  display: grid;
  gap: 7px;
  align-items: center;
  margin-bottom: 8px;
}

.measure-config-row {
  grid-template-columns: minmax(140px, 1fr) minmax(160px, 1fr) minmax(160px, 1fr) 32px;
}

.measure-aggregation {
  display: flex;
  grid-column: 1 / -1;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
}

.measure-aggregation .el-select {
  width: 180px;
}

.measure-derivatives-summary {
  grid-column: 1 / -1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin: 0 0 10px;
  padding: 7px 10px;
  border: 1px dashed #dbe8f5;
  border-radius: 6px;
  background: #f8fbff;
  color: #475d74;
  font-size: 12px;
}

.measure-derivatives-text {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}

.measure-derivatives-text small {
  font-weight: 400;
}

.formula-inputs {
  grid-column: 1 / -1;
  display: grid;
  gap: 8px;
  margin-bottom: 10px;
}

.formula-overview {
  display: grid;
  gap: 5px;
  padding: 8px 10px;
  border: 1px solid #dbe8f5;
  border-radius: 6px;
  background: #f5faff;
}

.formula-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.formula-line code {
  padding: 2px 6px;
  border-radius: 4px;
  background: #fff;
  color: #2c5879;
  font-size: 12px;
  word-break: break-all;
}

.formula-label {
  flex: none;
  color: var(--muted);
  font-size: 11px;
}

.formula-description {
  padding-left: 64px;
  color: #52647a;
  font-size: 12px;
  line-height: 1.5;
}

.formula-operands {
  display: grid;
  gap: 6px;
}

.formula-operand-row {
  display: grid;
  grid-template-columns: 44px 110px minmax(0, 1fr);
  gap: 4px 8px;
  align-items: center;
}

.operand-token {
  padding: 0 6px;
  border-radius: 4px;
  background: #eef5fb;
  color: #2c5879;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  line-height: 24px;
  text-align: center;
}

.operand-meaning {
  overflow: hidden;
  color: #475d74;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.operand-selected {
  grid-column: 3;
  margin-top: -2px;
  color: var(--muted);
  font-size: 11px;
}

.formula-tip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  margin-top: 4px;
  padding: 6px 8px;
  border: 1px solid #f2e2b8;
  border-radius: 5px;
  background: #fff8e6;
  color: #a06a1b;
  font-size: 11px;
}

.derivative-dialog {
  display: grid;
  gap: 12px;
}

.derivative-dialog-tip {
  color: var(--muted);
  font-size: 12px;
}

.derivative-block {
  padding: 10px;
  border: 1px solid var(--line-soft);
  border-radius: 6px;
  background: #fbfdff;
}

.derivative-block-head {
  display: grid;
  gap: 2px;
  margin-bottom: 6px;
}

.derivative-check-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0 14px;
}

.derivative-check-group :deep(.el-checkbox) {
  margin-right: 0;
}

.measure-config-guide {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 90px minmax(0, 1fr);
  gap: 7px;
  margin: 2px 0 6px;
  padding: 0 1px;
}

.measure-config-guide div {
  min-width: 0;
}

.measure-config-guide b,
.measure-config-guide span {
  display: block;
}

.measure-config-guide b {
  color: #475d74;
  font-size: 11px;
}

.measure-config-guide span {
  margin-top: 2px;
  color: var(--muted);
  font-size: 10px;
  white-space: nowrap;
}

.measure-section .section-help {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 11px;
  font-weight: 400;
  line-height: 1.5;
}

.measure-example {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 14px;
  margin-top: 4px;
  padding: 8px 9px;
  border: 1px solid #dbe8f5;
  background: #f5faff;
  color: #52647a;
  font-size: 11px;
  line-height: 1.5;
}

.measure-example b {
  color: var(--brand);
}

.measure-example strong {
  color: #2c5879;
  font-weight: 700;
}

.filter-config-row {
  grid-template-columns: 52px minmax(0, 1fr) 70px minmax(0, 1fr) 32px;
}

.filter-first {
  color: var(--muted);
  text-align: center;
  font-size: 12px;
}

.derived-compact {
  background: #f8fbfe;
}

.compact-builder-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

.sql-preview-section .sql {
  min-height: 120px;
  max-height: 320px;
}

.trial-hint {
  color: var(--muted);
  font-size: 12px;
}

.trial-error {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px solid #f5c2c2;
  background: #fff5f5;
  color: #c45656;
  font-size: 12px;
  border-radius: 6px;
}

.trial-result {
  margin-top: 10px;
  border: 1px solid var(--line-soft);
  border-radius: 6px;
  background: #fff;
  padding: 8px;
}

.trial-result-title {
  margin-bottom: 6px;
  color: var(--ink);
  font-size: 12px;
  font-weight: 600;
}

.trial-empty {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px dashed var(--line-soft);
  background: #fbfdff;
  color: var(--muted);
  font-size: 12px;
  border-radius: 6px;
}

.builder-check-row { display: flex; width: 100%; margin: 0; padding: 9px 10px; border-bottom: 1px solid #eef2f6; }
.builder-check-row small { display: block; color: var(--muted); }
.compact-builder { width: 100%;}

@media (max-width: 1200px) {
  .basic-form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .basic-span-2 {
    grid-column: 1 / -1;
  }

  .basic-span-all {
    grid-column: 1 / -1;
  }
}

@media (max-width: 1000px) {
  .builder-config-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .basic-form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .measure-config-row {
    grid-template-columns: 1fr 1fr 32px;
    align-items: end;
  }

  .measure-config-guide {
    display: none;
  }

  .filter-config-row {
    grid-template-columns: 1fr 1fr;
  }
}
.formula-system-note {
  margin-top: 6px;
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.5;
  border-radius: 4px;
  background-color: #f0f5ff;
  color: #3a6fb5;
}
.formula-system-note.warning {
  background-color: #fff7e6;
  color: #c27500;
}
.formula-system-note code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 0 4px;
  border-radius: 3px;
  font-size: 11px;
}
.trial-section .trial-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.trial-section .trial-date-label {
  font-size: 12px;
  color: var(--ink-3);
}
.trial-section .trial-date-item {
  margin-bottom: 0;
}
.trial-section .trial-date-item :deep(.el-date-editor) {
  width: 160px;
}
.trial-section .trial-date-item:last-child {
  margin-right: 4px;
}
</style>
