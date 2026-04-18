/** 全局状态 - 当前登录用户 & API工具
 *  V5.1引入角色体系, V5.3前端配合角色切换模拟登录
 */
import { defineStore } from 'pinia'
import axios from 'axios'

// 预置的模拟用户列表（与init_db.py种子数据一致）
const MOCK_USERS = [
  { emp_id: 'EMP001', name: '科长A',  role: '科长级' },
  { emp_id: 'EMP002', name: '采购牛马B', role: '采购科' },
  { emp_id: 'EMP003', name: '员工C',  role: '普通员工' },
]

const api = axios.create({ baseURL: '/api' })

export const useAppStore = defineStore('app', {
  state: () => ({
    currentUser: null,       // 当前登录用户对象
    mockUsers: MOCK_USERS,   // 可切换的用户列表
  }),

  getters: {
    empId:   (s) => s.currentUser?.emp_id ?? '',
    role:    (s) => s.currentUser?.role ?? '',
    name:    (s) => s.currentUser?.name ?? '',
    isChief: (s) => s.currentUser?.role === '科长级',
    isPurchase: (s) => s.currentUser?.role === '采购科',
  },

  actions: {
    /** 切换模拟登录用户 */
    switchUser(empId) {
      this.currentUser = this.mockUsers.find(u => u.emp_id === empId) || null
    },

    /** 带认证Header的API请求 */
    async request(method, path, data = null) {
      const headers = { 'X-Emp-Id': this.empId }
      const res = await api({ method, url: path, data, headers })
      return res.data
    },
  },
})