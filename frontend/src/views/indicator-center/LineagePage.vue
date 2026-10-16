<template>
    <div class="page">
      <div class="page-head"><div><h1>血缘分析</h1><div class="desc">展示物理表、模型、指标和结果表之间的上下游关系。</div></div></div>
      <div class="filterbar version-filter"><div class="filter-item"><span>选择指标</span><el-select v-model="selectedId" style="width:100%"><el-option v-for="i in data.indicators" :key="i.id" :value="i.id" :label="`${i.name} (${i.code})`" /></el-select></div></div>
      <el-card v-if="indicator && model" shadow="never">
        <div class="lineage wide-lineage">
          <div><span>物理表</span><b>{{ model.table }}</b></div><i></i>
          <div><span>业务模型</span><b>{{ model.name }}</b></div><i></i>
          <div><span>指标</span><b>{{ indicator.name }}</b></div><i></i>
          <div><span>结果表</span><b>{{ resultTable }}</b></div>
        </div>
      </el-card>
      <div class="grid-2" v-if="indicator && model">
        <el-card shadow="never">
          <template #header><div class="head-bar"><strong>字段血缘</strong></div></template>
          <el-table :data="fieldLineage" size="small" empty-text="暂无字段">
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="biz" label="业务字段" min-width="140" show-overflow-tooltip />
            <el-table-column prop="phys" label="物理字段" min-width="200" show-overflow-tooltip />
          </el-table>
        </el-card>
        <el-card shadow="never">
          <template #header><div class="head-bar"><strong>关联模型</strong></div></template>
          <el-table :data="joinModels" size="small" empty-text="未配置关联模型">
            <el-table-column prop="name" label="模型" min-width="140" show-overflow-tooltip />
            <el-table-column prop="table" label="物理表" min-width="140" show-overflow-tooltip />
            <el-table-column prop="module" label="模块" width="120" />
          </el-table>
        </el-card>
      </div>
    </div>

</template>

<script lang="ts">
import { defineComponent, ref, ref as vueRef, computed as vueComputed, watch as vueWatch } from 'vue'
import { api as requestApi } from '../../api'
import type { BootstrapData, Indicator as IndicatorT, IndicatorMeasure, ModelOption as ModelOptionT } from '../../types'

function getMeasures(indicator: { config: { measures?: IndicatorMeasure[]; measure?: IndicatorMeasure } }): IndicatorMeasure[] {
  return indicator.config.measures ?? (indicator.config.measure ? [indicator.config.measure] : [])
}

function getDimensions(indicator: { config: { dimensions?: Array<{ fieldName: string; alias?: string }> } }) {
  return Array.isArray(indicator.config.dimensions) ? indicator.config.dimensions : []
}

function getJoins(indicator: { config: { joins?: Array<{ modelId: string }> } }) {
  return Array.isArray(indicator.config.joins) ? indicator.config.joins : []
}

function getResultTable(indicator: { config: { schedule?: { resultTable?: string } } }) {
  return indicator.config.schedule?.resultTable || 'T_IND_RESULT_D'
}

const LineagePage = defineComponent({
  props: { data: { type: Object as () => BootstrapData, required: true }, indicatorId: { type: String, default: '' } },
  setup(props) {
    const selectedId = vueRef(props.indicatorId || props.data.indicators[0]?.id || '')
    const indicator = vueRef<IndicatorT | null>(null)
    const model = vueComputed(() => props.data.models.find((m) => m.id === indicator.value?.modelId))
    const joinModels = vueComputed(() => (indicator.value ? getJoins(indicator.value) : []).map((j) => props.data.models.find((m) => m.id === j.modelId)).filter((m): m is ModelOptionT => Boolean(m)))
    const resultTable = vueComputed(() => indicator.value ? getResultTable(indicator.value) : 'T_IND_RESULT_D')
    const fieldLineage = vueComputed(() => {
      const rows: Array<{ type: string; biz: string; phys: string }> = []
      if (!indicator.value || !model.value) return rows
      getDimensions(indicator.value).forEach((d) => rows.push({ type: '维度', biz: d.alias || d.fieldName, phys: `${model.value!.table}.${d.fieldName}` }))
      getMeasures(indicator.value).forEach((m) => rows.push({ type: '度量', biz: m.alias || m.fieldName, phys: `${model.value!.table}.${m.fieldName}` }))
      return rows
    })
    async function loadIndicator() {
      if (!selectedId.value) { indicator.value = null; return }
      try {
        indicator.value = await requestApi<IndicatorT>('/api/indicators/' + selectedId.value)
      } catch {
        indicator.value = null
      }
    }
    vueWatch(selectedId, loadIndicator, { immediate: true })
    vueWatch(() => props.indicatorId, (id) => { if (id) selectedId.value = id })
    return { selectedId, indicator, model, joinModels, resultTable, fieldLineage }
  },

})

export default LineagePage
</script>

<style scoped>
.lineage {
  display: grid;
  grid-template-columns: 1fr 28px 1fr 28px 1fr 28px 1fr;
  align-items: center;
  gap: 6px;
}

.wide-lineage {
  grid-template-columns: 1fr 28px 1fr 28px 1fr 28px 1fr 28px 1fr;
}

.lineage div {
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--soft);
  padding: 10px;
}

.lineage span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 3px;
}

.lineage i {
  display: block;
  height: 1px;
  background: #9fb7cf;
  position: relative;
}

.lineage i::after {
  content: "";
  position: absolute;
  right: 0;
  top: -4px;
  border-left: 6px solid #9fb7cf;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
}
.head-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.head-bar strong { color: var(--ink); }
</style>
