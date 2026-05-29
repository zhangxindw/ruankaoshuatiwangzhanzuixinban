<template>
  <div class="chapters-view">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2>章节管理</h2>
        <p>管理题库章节分类，支持多级分类</p>
      </div>
      <el-button type="primary" @click="showDialog('create')">
        <el-icon><Plus /></el-icon>
        新建章节
      </el-button>
    </div>

    <div class="card">
      <div class="chapter-stats">
        <div class="stat-item">
          <span class="stat-label">章节总数</span>
          <span class="stat-value">{{ totalChapters }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">题目总数</span>
          <span class="stat-value">{{ totalQuestions }}</span>
        </div>
      </div>
      
      <el-tree
        :data="treeData"
        :props="{ children: 'children', label: 'name' }"
        node-key="id"
        default-expand-all
        style="background: transparent;"
      >
        <template #default="{ node, data }">
          <span class="tree-node">
            <span class="chapter-info">
              <el-icon class="chapter-icon"><Folder /></el-icon>
              <span class="chapter-name">{{ node.label }}</span>
              <el-tag size="small" type="info" class="question-count-tag">
                <el-icon><Document /></el-icon>
                {{ data.question_count || 0 }} 题
              </el-tag>
            </span>
            <span class="tree-actions">
              <el-button size="small" type="text" @click.stop="showDialog('createChild', data)">添加子章节</el-button>
              <el-button size="small" type="text" @click.stop="showDialog('edit', data)">编辑</el-button>
              <el-button size="small" type="text" danger @click.stop="deleteChapter(data)">删除</el-button>
            </span>
          </span>
        </template>
      </el-tree>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="章节名称">
          <el-input v-model="form.name" placeholder="请输入章节名称" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useQuizStore } from '@/store/quiz'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder, Document, Plus } from '@element-plus/icons-vue'

const store = useQuizStore()

const treeData = ref([])
const dialogVisible = ref(false)
const dialogType = ref('create')
const currentNode = ref(null)
const form = reactive({
  name: '',
  order: 0,
  parent_id: null
})

const totalChapters = computed(() => {
  const countChapters = (chapters) => {
    let count = 0
    for (const ch of chapters) {
      count++
      if (ch.children && ch.children.length > 0) {
        count += countChapters(ch.children)
      }
    }
    return count
  }
  return countChapters(treeData.value)
})

const totalQuestions = computed(() => {
  const countQuestions = (chapters) => {
    let count = 0
    for (const ch of chapters) {
      count += (ch.question_count || 0)
      if (ch.children && ch.children.length > 0) {
        count += countQuestions(ch.children)
      }
    }
    return count
  }
  return countQuestions(treeData.value)
})

const dialogTitle = computed(() => {
  if (dialogType.value === 'create') return '新建章节'
  if (dialogType.value === 'createChild') return '添加子章节'
  return '编辑章节'
})

const loadChapters = async () => {
  await store.loadChapters()
  treeData.value = store.chapters
}

const showDialog = (type, data = null) => {
  dialogType.value = type
  currentNode.value = data
  if (type === 'edit' && data) {
    form.name = data.name
    form.order = data.order || 0
    form.parent_id = data.parent_id
  } else if (type === 'createChild' && data) {
    form.name = ''
    form.order = 0
    form.parent_id = data.id
  } else {
    form.name = ''
    form.order = 0
    form.parent_id = null
  }
  dialogVisible.value = true
}

const saveChapter = async () => {
  if (!form.name) {
    ElMessage.warning('请输入章节名称')
    return
  }

  try {
    if (dialogType.value === 'edit' && currentNode.value) {
      await store.updateChapter(currentNode.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await store.createChapter(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadChapters()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deleteChapter = async (data) => {
  try {
    await ElMessageBox.confirm(`确定要删除章节"${data.name}"吗？删除后该章节下的题目将变为未分类状态。`, '提示', { type: 'warning' })
    await store.deleteChapter(data.id)
    ElMessage.success('删除成功')
    loadChapters()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadChapters()
})
</script>

<style scoped>
.chapters-view {
  padding: 20px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.chapter-stats {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
  padding: 15px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
}

.tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.3s;
}

.tree-node:hover {
  background: #f5f7fa;
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.chapter-icon {
  color: #409EFF;
  font-size: 18px;
}

.chapter-name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.question-count-tag {
  margin-left: 8px;
}

.question-count-tag .el-icon {
  margin-right: 3px;
}

.tree-actions {
  display: none;
  gap: 5px;
}

.tree-node:hover .tree-actions {
  display: flex;
}

:deep(.el-tree-node__content) {
  height: auto;
  padding: 4px 0;
}

:deep(.el-tree) {
  background: transparent;
}
</style>
