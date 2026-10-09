import { defineStore } from 'pinia'

export const useApplicationStore = defineStore('application', {
  state: () => ({
    title: 'Spark 学习分析',
    stage: '本科毕业设计 · 前端基础架构阶段',
  }),
})

