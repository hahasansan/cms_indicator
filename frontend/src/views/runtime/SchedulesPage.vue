<template>
<div class="page data-list-page">
  <div class="page-head"><div><h1>调度管理</h1><div class="desc">配置指标跑批频率、时间和业务日期，到点自动触发；也可手动触发。</div></div><el-button type="primary" @click="openCreate">新增调度</el-button></div>
  <el-card shadow="never" class="data-list-main data-list-panel">
    <el-table :data="data.schedules" size="small" empty-text="暂无调度任务">
      <el-table-column prop="name" label="调度" min-width="150" show-overflow-tooltip />
      <el-table-column label="指标" min-width="160"><template #default="{ row }">{{ row.indicator_name || row.indicator_id }}</template></el-table-column>
      <el-table-column label="范围" width="90"><template #default="{ row }">{{ row.scope === 'all' ? '全部' : row.scope === 'category' ? '按分类' : '指定指标' }}</template></el-table-column>
      <el-table-column prop="frequency" label="频率" width="80" />
      <el-table-column prop="run_time" label="时间" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }"><el-tag size="small" :type="row.enabled ? 'success' : 'danger'">{{ row.enabled ? 'enabled' : 'disabled' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="上次 / 下次" min-width="180"><template #default="{ row }">{{ row.last_run_at || '-' }}<br />{{ row.next_run_at || '-' }}</template></el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="run(row.id)">触发</el-button>
          <el-button size="small" type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogOpen" title="新增调度" width="620px" append-to-body>
    <el-form label-width="90px">
      <el-form-item label="调度名称" required><el-input v-model="form.name" placeholder="例如：每日债券持仓跑批" /></el-form-item>
      <el-form-item label="运行范围">
        <el-select v-model="form.scope" style="width:100%">
          <el-option value="selected" label="指定指标" />
          <el-option value="all" label="全部指标" />
          <el-option value="category" label="按分类" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.scope==='selected'" label="指标" required>
        <el-select v-model="form.indicatorId" style="width:100%" @change="applyIndicatorBizDateType"><el-option v-for="i in data.indicators" :key="i.id" :value="i.id" :label="`${i.name}（${i.code}）`" /></el-select>
      </el-form-item>
      <el-form-item v-if="form.scope==='category'" label="分类" required>
        <el-select v-model="form.categoryId" style="width:100%"><el-option v-for="c in data.indicatorCategories.filter(x=>x.id!=='root')" :key="c.id" :value="c.id" :label="c.name" /></el-select>
      </el-form-item>
      <el-form-item label="频率" required>
        <el-select v-model="form.frequency" style="width:100%"><el-option value="日" label="日" /><el-option value="周" label="周" /><el-option value="月" label="月" /><el-option value="季度" label="季度" /><el-option value="年" label="年" /><el-option value="手动" label="手动" /></el-select>
        <div class="muted" style="font-size:12px;margin-top:4px">周固定在周日、月/季度/年固定在期末运行</div>
      </el-form-item>
      <el-form-item label="时间" required><el-input v-model="form.runTime" placeholder="例如 02:00" /></el-form-item>
      <el-form-item label="业务类型">
        <el-select v-model="form.dateType" style="width:100%" :disabled="form.scope==='selected'"><el-option value="balance" label="余额类（单日）" /><el-option value="period" label="时段类（区间）" /></el-select>
      </el-form-item>
      <template v-if="form.dateType==='period'">
        <el-form-item label="开始日期" required>
          <el-select v-model="form.startOption" style="width:100%">
            <el-option value="week_start" label="本周一" />
            <el-option value="month_start" label="本月初" />
            <el-option value="quarter_start" label="本季初" />
            <el-option value="year_start" label="年初" />
            <el-option value="month" label="月份" />
            <el-option value="specific" label="具体日期" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.startOption==='month'" label="月份" required><el-input v-model="form.startMonth" type="month" /></el-form-item>
        <el-form-item v-if="form.startOption==='specific'" label="日期" required><el-input v-model="form.startSpecific" type="date" /></el-form-item>
        <el-form-item label="结束日期" required>
          <el-select v-model="form.endOption" style="width:100%"><el-option value="today" label="调度日期" /><el-option value="t1" label="T-1" /><el-option value="last_workday" label="最近工作日" /><el-option value="specific" label="具体日期" /></el-select>
        </el-form-item>
        <el-form-item v-if="form.endOption==='specific'" label="日期" required><el-input v-model="form.endSpecific" type="date" /></el-form-item>
      </template>
      <template v-else>
        <el-form-item label="业务日期" required>
          <el-select v-model="form.singleOption" style="width:100%"><el-option value="today" label="今天" /><el-option value="last_workday" label="最近工作日" /><el-option value="specific" label="具体日期" /></el-select>
        </el-form-item>
        <el-form-item v-if="form.singleOption==='specific'" label="日期" required><el-input v-model="form.singleSpecific" type="date" /></el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="dialogOpen=false">取消</el-button>
      <el-button type="primary" @click="save">保存调度</el-button>
    </template>
  </el-dialog>
</div>
</template>

<script lang="ts">
import { defineComponent, inject, reactive as vueReactive, ref as vueRef } from 'vue'
import { api as requestApi, jsonBody as toJsonBody } from '../../api'
import type { BootstrapData } from '../../types'

const ToastInject = 'notify'

function useNotify() {
  return inject<(message: string) => void>(ToastInject, () => undefined)
}

const SchedulesPage = defineComponent({
  props: { data: { type: Object as () => BootstrapData, required: true } },
  emits: ['reload'],
  setup(props, { emit }) {
    const notify = useNotify()
    const dialogOpen = vueRef(false)
    const form = vueReactive({
      name: '',
      indicatorId: '',
      scope: 'selected',
      categoryId: '',
      frequency: '日',
      runTime: '02:00',
      dateType: 'balance',
      singleOption: 'today',
      singleSpecific: '',
      startOption: 'month_start',
      startMonth: '',
      startSpecific: '',
      endOption: 'today',
      endSpecific: '',
    })
    // 单个指标调度：业务类型跟随指标自身保存的业务时间参数
    function applyIndicatorBizDateType() {
      if (form.scope !== 'selected') return
      const indicator = props.data.indicators.find((item) => item.id === form.indicatorId)
      if (indicator?.bizDateType) form.dateType = indicator.bizDateType
    }
    function openCreate() {
      form.name = ''
      form.indicatorId = props.data.indicators[0]?.id || ''
      form.scope = 'selected'
      form.categoryId = ''
      form.frequency = '日'
      form.runTime = '02:00'
      form.dateType = 'balance'
      form.singleOption = 'today'; form.singleSpecific = ''
      form.startOption = 'month_start'; form.startMonth = ''; form.startSpecific = ''
      form.endOption = 'today'; form.endSpecific = ''
      applyIndicatorBizDateType()
      dialogOpen.value = true
    }
    function buildDateOption() {
      if (form.dateType === 'period') {
        return {
          type: 'period',
          start: { option: form.startOption, value: form.startOption === 'month' ? form.startMonth : (form.startOption === 'specific' ? form.startSpecific : '') },
          end: { option: form.endOption, value: form.endOption === 'specific' ? form.endSpecific : '' },
        }
      }
      return { type: 'balance', single: { option: form.singleOption, value: form.singleOption === 'specific' ? form.singleSpecific : '' } }
    }
    async function save() {
      if (!form.name.trim()) { notify('请填写调度名称'); return }
      if (form.scope === 'selected' && !form.indicatorId) { notify('请选择指标'); return }
      if (form.scope === 'category' && !form.categoryId) { notify('请选择分类'); return }
      await requestApi('/api/schedules', {
        method: 'POST',
        body: toJsonBody({ indicatorId: form.indicatorId, name: form.name, frequency: form.frequency, runTime: form.runTime, enabled: true, dateOption: buildDateOption(), scope: form.scope, categoryId: form.categoryId }),
      })
      notify('调度已保存')
      dialogOpen.value = false
      emit('reload')
    }
    async function run(id: string) {
      const s = props.data.schedules.find((x) => x.id === id)
      const body: Record<string, unknown> = {}
      if (s?.dateOption) body.dateOption = s.dateOption
      const res = await requestApi<{ total: number; success: number; failed: number; details: Array<{ indicatorCode: string; status: string; rowCount?: number; message?: string }> }>(`/api/schedules/${id}/runs`, { method: 'POST', body: toJsonBody(body) })
      const rows = res.details.reduce((sum, d) => sum + (d.rowCount ?? 0), 0)
      if (res.failed > 0) {
        const firstFail = res.details.find((d) => d.status === 'failed')
        notify(`调度完成：成功 ${res.success} 个，失败 ${res.failed} 个，写入 ${rows} 行${firstFail?.message ? `，首个失败原因：${firstFail.message}` : ''}`)
      } else {
        notify(`调度触发成功，写入 ${rows} 行`)
      }
      emit('reload')
    }
    async function remove(id: string) {
      await requestApi(`/api/schedules/${id}`, { method: 'DELETE' })
      notify('调度已删除')
      emit('reload')
    }
    return { dialogOpen, form, openCreate, applyIndicatorBizDateType, save, run, remove }
  },

})

export default SchedulesPage
</script>
