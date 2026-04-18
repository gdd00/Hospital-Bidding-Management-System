/** 全局状态 - 登录认证 + 权限检查 + API请求
 *  V5.3重构: 移除mock切换，改为真正的token登录
 *  权限从硬编码角色改为读取user.permissions数组
 */
import { defineStore } from 'pinia'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const useAppStore = defineStore('app', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    currentUser: null,  // {id, emp_id, name, group_name, permissions}
  }),

  getters: {
    isLoggedIn: (s) => !!s.token && !!s.currentUser,
    empId:      (s) => s.currentUser?.emp_id ?? '',
    name:       (s) => s.currentUser?.name ?? '',
    groupName:  (s) => s.currentUser?.group_name ?? '',
    permissions: (s) => s.currentUser?.permissions ?? [],

    // 便捷权限getter
    canCreateProject:     (s) => s.currentUser?.permissions?.includes('create_project'),
    canWriteProcurement:  (s) => s.currentUser?.permissions?.includes('write_procurement'),
    canAdvanceStatus:     (s) => s.currentUser?.permissions?.includes('advance_status'),
    canAdvanceToSupplier: (s) => s.currentUser?.permissions?.includes('advance_to_supplier'),
    canViewDashboard:     (s) => s.currentUser?.permissions?.includes('view_dashboard'),
    canManageAccounts:    (s) => s.currentUser?.permissions?.includes('manage_accounts'),
  },

  actions: {
    /** 登录 */
    async login(empId, password) {
      const res = await api.post('/auth/login', { emp_id: empId, password })
      this.token = res.data.token
      this.currentUser = res.data.user
      localStorage.setItem('token', this.token)
      // 后端已通过Cookie下发token，axios后续请求自动携带
      return res.data
    },

    /** 登出 */
    async logout() {
      try {
        await api.post('/auth/logout', null, this._authConfig())
      } catch { /* 静默 */ }
      this.token = ''
      this.currentUser = null
      localStorage.removeItem('token')
    },

    /** 拉取当前用户信息(恢复登录态) */
    async fetchMe() {
      if (!this.token) return
      try {
        const res = await api.get('/auth/me', this._authConfig())
        this.currentUser = res.data
      } catch {
        // token过期，清除
        this.token = ''
        this.currentUser = null
        localStorage.removeItem('token')
      }
    },

    /** 带认证的API请求 */
    async request(method, path, data = null) {
      const res = await api({ method, url: path, data, ...this._authConfig() })
      return res.data
    },

    /** 生成认证请求配置 */
    _authConfig() {
      return { headers: { Authorization: `Bearer ${this.token}` } }
    },
  },
})