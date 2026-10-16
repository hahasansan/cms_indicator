import { defineStore } from 'pinia'
import { api } from '../api'
import type { BootstrapData, IndicatorCategory, ModelOption, IndicatorOption, Schedule } from '../types'

export const useAppStore = defineStore('app', {
  state: () => ({
    data: null as BootstrapData | null,
    loading: false,
    error: '',
  }),
  actions: {
    // 预加载轻量 options（下拉/统计用）；列表页各自按需调分页接口
    async load() {
      this.loading = true
      this.error = ''
      try {
        const [models, indicators, indicatorCategories, schedules, jobs] = await Promise.all([
          api<ModelOption[]>('/api/models/options'),
          api<IndicatorOption[]>('/api/indicators/options'),
          api<IndicatorCategory[]>('/api/indicator-categories'),
          api<Schedule[]>('/api/schedules'),
          api<Record<string, unknown>[]>('/api/jobs'),
        ])
        this.data = { models, indicators, indicatorCategories, schedules, jobs }
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
  },
})
