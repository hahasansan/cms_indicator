<template>
<div class="page data-list-page">
  <div class="page-head"><div><h1>运行日志</h1><div class="desc">记录每次指标运行状态、SQL、行数和错误信息。</div></div></div>
  <el-card shadow="never" class="data-list-main data-list-panel">
    <el-table :data="data.jobs" size="small" empty-text="暂无运行记录">
      <el-table-column v-for="key in jobKeys" :key="key" :prop="key" :label="key" min-width="120" show-overflow-tooltip />
    </el-table>
  </el-card>
</div>
</template>

<script lang="ts">
import { defineComponent, computed as vueComputed } from 'vue'
import type { BootstrapData } from '../../types'

const JobsPage = defineComponent({
  props: { data: { type: Object as () => BootstrapData, required: true } },
  setup(props) {
    const jobKeys = vueComputed(() => props.data.jobs.length ? Object.keys(props.data.jobs[0]) : [])
    return { jobKeys }
  },

})

export default JobsPage
</script>
