<template>
  <!-- V5.3登录页 - 真正的工号+密码认证 -->
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">医院招投标管理系统</h2>
      <span class="login-version">V5.3</span>

      <el-form :model="form" @submit.prevent="onLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="form.empId"
            placeholder="工号 (如 EMP001)"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码 (初始密码=工号)"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            style="width: 100%"
            @click="onLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <el-collapse class="login-hint">
        <el-collapse-item title="测试账号提示">
          <div class="hint-content">
            <p>EMP001 / EMP001 — 科长A (科长组)</p>
            <p>EMP002 / EMP002 — 采购牛马B (采购组)</p>
            <p>EMP003 / EMP003 — 员工C (员工组)</p>
            <p class="hint-note">初始密码统一为工号本身</p>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const emit = defineEmits(['login-success'])

const form = reactive({ empId: '', password: '' })
const loading = ref(false)

async function onLogin() {
  if (!form.empId || !form.password) {
    ElMessage.warning('请输入工号和密码')
    return
  }
  loading.value = true
  try {
    await store.login(form.empId, form.password)
    ElMessage.success(`登录成功: ${store.name} (${store.groupName})`)
    emit('login-success')
  } catch (e) {
    const detail = e.response?.data?.detail || '登录失败'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #001529 0%, #003a70 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-card {
  width: 400px;
  background: #fff;
  border-radius: 8px;
  padding: 40px 32px 24px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}
.login-title {
  text-align: center;
  margin: 0;
  font-size: 22px;
  color: #001529;
}
.login-version {
  display: block;
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-bottom: 32px;
}
.login-hint {
  margin-top: 16px;
}
.hint-content p {
  margin: 4px 0;
  font-size: 13px;
}
.hint-note {
  color: #e6a23c;
  font-weight: 500;
}
</style>