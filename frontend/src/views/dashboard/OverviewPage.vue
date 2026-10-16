<template>
    <div class="page">
      <div class="page-head">
        <div>
          <h1>从业务口径到可执行指标</h1>
          <div class="desc">Vue3 版本已接入后端 API，支持模型、指标加工、指标管理、结果查询和调度管理。</div>
        </div>
        <div class="actions">
          <el-button type="primary" @click="emit('go','indicators')">进入指标管理</el-button>
        </div>
      </div>
      <div class="grid-4">
        <div class="stat" v-for="s in stats" :key="s[0]">
          <div class="stat-icon">◆</div>
          <div><div class="stat-value">{{ s[1] }}</div><div class="stat-label">{{ s[0] }} · {{ s[2] }}</div></div>
        </div>
      </div>
      <div class="grid-2">
        <el-card shadow="never">
          <template #header><div class="head-bar"><strong>最近指标</strong></div></template>
          <el-table :data="data.indicators.slice(0,5)" size="small" empty-text="暂无指标">
            <el-table-column prop="name" label="指标" min-width="160" show-overflow-tooltip />
            <el-table-column prop="code" label="编码" width="120" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="row.status==='enabled' ? 'success' : 'info'">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="updatedAt" label="更新时间" width="160" />
          </el-table>
        </el-card>
        <el-card shadow="never">
          <template #header><div class="head-bar"><strong>流程</strong></div></template>
          <el-alert type="info" :closable="false" show-icon title="模型字段维护 → 指标加工 → SQL 试算 → 保存版本 → 运行写入结果表 → 查询指标结果。" />
        </el-card>
      </div>
    </div>

</template>

<script lang="ts">
import { defineComponent, computed as vueComputed } from 'vue'
import type { BootstrapData } from '../../types'

const OverviewPage = defineComponent({
  props: { data: { type: Object as () => BootstrapData, required: true } },
  emits: ['go'],
  setup(props, { emit }) {
    const stats = vueComputed(() => [
      ['数据模型', props.data.models.length, '业务元数据'],
      ['指标数量', props.data.indicators.length, '定义与版本'],
      ['调度任务', props.data.schedules.length, '定时运行'],
    ])
    return { stats, emit }
  },
})

export default OverviewPage
</script>

<style scoped>
.head-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.head-bar strong { color: var(--ink); }
</style>
