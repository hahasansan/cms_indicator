<template>
    <div class="page">
      <div class="page-head"><div><h1>影响性分析</h1><div class="desc">下线、禁用或调整指标前，查看调度、结果表、运行日志和同表指标影响范围。</div></div></div>
      <div class="filterbar version-filter"><div class="filter-item"><span>选择指标</span><el-select v-model="selectedId" style="width:100%"><el-option v-for="i in data.indicators" :key="i.id" :value="i.id" :label="`${i.name} (${i.code})`" /></el-select></div></div>
      <div class="grid-4" v-if="indicator">
        <div class="stat"><div class="stat-icon">调</div><div><div class="stat-value">{{ schedules.length }}</div><div class="stat-label">关联调度</div></div></div>
        <div class="stat"><div class="stat-icon">表</div><div><div class="stat-value">{{ resultTable }}</div><div class="stat-label">写入结果表</div></div></div>
        <div class="stat"><div class="stat-icon">志</div><div><div class="stat-value">{{ jobs.length }}</div><div class="stat-label">运行日志</div></div></div>
        <div class="stat"><div class="stat-icon">同</div><div><div class="stat-value">{{ sameResultIndicators.length }}</div><div class="stat-label">同表指标</div></div></div>
      </div>
      <div class="grid-2" v-if="indicator">
        <el-card shadow="never">
          <template #header><div class="head-bar"><strong>调度影响</strong></div></template>
          <el-table :data="schedules" size="small" empty-text="暂无调度">
            <el-table-column prop="name" label="调度" min-width="140" show-overflow-tooltip />
            <el-table-column prop="frequency" label="频率" width="80" />
            <el-table-column prop="run_time" label="时间" width="90" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="row.enabled ? 'success' : 'danger'">{{ row.enabled ? 'enabled' : 'disabled' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
        <el-card shadow="never">
          <template #header><div class="head-bar"><strong>同结果表指标</strong></div></template>
          <el-table :data="sameResultIndicators" size="small" empty-text="无同表指标">
            <el-table-column prop="name" label="指标" min-width="140" show-overflow-tooltip />
            <el-table-column prop="code" label="编码" width="110" />
            <el-table-column label="模型" min-width="130"><template #default="{ row }">{{ modelDisplayName(data.models, row.modelId) }}</template></el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="['enabled','success'].includes(row.status) ? 'success' : 'info'">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
      <el-card v-if="indicator" shadow="never">
        <template #header><div class="head-bar"><strong>变更建议</strong></div></template>
        <el-alert type="info" :closable="false" show-icon title="如果要禁用或下线该指标，请先确认调度是否停用、下游结果表是否仍被查询、同表指标是否依赖统一跑批窗口。" />
      </el-card>
    </div>

</template>

<script lang="ts">
import { defineComponent, ref, ref as vueRef, computed as vueComputed, watch as vueWatch } from 'vue'
import type { BootstrapData, ModelOption as ModelOptionT } from '../../types'

const DEFAULT_RESULT_TABLE = 'T_IND_RESULT_D'

function modelDisplayName(models: ModelOptionT[], modelId: string) {
  return models.find((m) => m.id === modelId)?.name ?? '-'
}

const ImpactPage = defineComponent({
  props: { data: { type: Object as () => BootstrapData, required: true }, indicatorId: { type: String, default: '' } },
  setup(props) {
    const selectedId = vueRef(props.indicatorId || props.data.indicators[0]?.id || '')
    const indicator = vueComputed(() => props.data.indicators.find((i) => i.id === selectedId.value))
    const schedules = vueComputed(() => props.data.schedules.filter((s) => s.indicator_id === selectedId.value))
    const jobs = vueComputed(() => props.data.jobs.filter((j) => j.indicator_id === selectedId.value))
    const resultTable = vueComputed(() => indicator.value ? (indicator.value.resultTable || DEFAULT_RESULT_TABLE) : DEFAULT_RESULT_TABLE)
    const sameResultIndicators = vueComputed(() => props.data.indicators.filter((i) => i.id !== selectedId.value && (i.resultTable || DEFAULT_RESULT_TABLE) === resultTable.value))
    vueWatch(() => props.indicatorId, (id) => { if (id) selectedId.value = id })
    return { selectedId, indicator, schedules, jobs, resultTable, sameResultIndicators, modelDisplayName }
  },

})

export default ImpactPage
</script>

<style scoped>
.head-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.head-bar strong { color: var(--ink); }
</style>
