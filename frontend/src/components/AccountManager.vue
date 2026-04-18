<template>
  <!-- V5.3账号管理弹窗 - 仅manage_accounts权限可见 -->
  <el-dialog title="账号管理" :model-value="visible" width="700px" @close="$emit('close')">
    <!-- 新增账号 -->
    <el-form :model="newAccount" label-width="80px" inline style="margin-bottom: 16px">
      <el-form-item label="工号">
        <el-input v-model="newAccount.emp_id" placeholder="EMP004" style="width: 120px" />
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="newAccount.name" placeholder="新员工姓名" style="width: 120px" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="newAccount.password" placeholder="初始密码" style="width: 120px" />
      </el-form-item>
      <el-form-item label="分组">
        <el-select v-model="newAccount.group_name" style="width: 120px">
          <el-option v-for="g in groups" :key="g.name" :label="g.name" :value="g.name" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="creating" @click="createAccount">添加账号</el-button>
      </el-form-item>
    </el-form>

    <!-- 账号列表 -->
    <el-table :data="accounts" stripe border>
      <el-table-column prop="emp_id" label="工号" width="100" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="group_name" label="分组" width="100" />
      <el-table-column label="权限" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="p in row.permissions" :key="p" size="small" style="margin: 2px">
            {{ permLabel(p) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-select
            v-model="row._newGroup"
            size="small"
            style="width: 100px"
            @change="changeGroup(row)"
          >
            <el-option v-for="g in groups" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const emit = defineEmits(['close', 'changed'])

const props = defineProps({ visible: Boolean })

const accounts = ref([])
const groups = ref([])
const creating = ref(false)

const newAccount = reactive({
  emp_id: '',
  name: '',
  password: '',
  group_name: '员工组',
})

// 权限key → 中文label
function permLabel(key) {
  const map = {
    create_project: '创建项目',
    write_procurement: '录入采购',
    advance_status: '推进状态',
    advance_to_supplier: '推进寻源',
    view_dashboard: '查看看板',
    manage_accounts: '管理账号',
  }
  return map[key] || key
}

async function loadData() {
  accounts.value = await store.request('GET', '/accounts')
  groups.value = await store.request('GET', '/groups')
  // 为每行添加临时编辑字段
  accounts.value.forEach(a => a._newGroup = a.group_name)
}

watch(() => props.visible, (v) => { if (v) loadData() })

async function createAccount() {
  if (!newAccount.emp_id || !newAccount.name || !newAccount.password) {
    ElMessage.warning('请填写工号、姓名和密码')
    return
  }
  creating.value = true
  try {
    await store.request('POST', '/accounts', newAccount)
    ElMessage.success('账号已创建')
    newAccount.emp_id = ''
    newAccount.name = ''
    newAccount.password = ''
    await loadData()
    emit('changed')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function changeGroup(row) {
  try {
    await store.request('PUT', `/accounts/${row.id}/group`, { group_name: row._newGroup })
    ElMessage.success(`已将 ${row.name} 切换到 ${row._newGroup}`)
    await loadData()
    emit('changed')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}
</script>