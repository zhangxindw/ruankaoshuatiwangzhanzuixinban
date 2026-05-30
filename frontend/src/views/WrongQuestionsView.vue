<template>
  <div class="wrong-questions-view">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2>错题本</h2>
        <p>管理所有答错的题目，方便针对性复习</p>
      </div>
      <div>
        <el-button type="primary" @click="showChapterSelectDialog">
          <el-icon><RefreshRight /></el-icon>
          刷错题
        </el-button>
        <el-button type="danger" @click="clearAll">
          <el-icon><Delete /></el-icon>
          清空错题本
        </el-button>
      </div>
    </div>

    <!-- 章节选择对话框 -->
    <el-dialog v-model="chapterSelectVisible" title="选择刷错题范围" width="600px">
      <div class="chapter-select-content">
        <div class="chapter-select-header">
          <el-checkbox v-model="selectAllChapters" @change="handleSelectAll" style="font-weight: 500;">
            全选所有章节
          </el-checkbox>
          <span class="selected-count">已选择 {{ selectedChapterCount }} 个章节</span>
        </div>
        <div class="chapter-list">
          <el-checkbox-group v-model="selectedChapterIds">
            <div v-for="chapter in store.chapters" :key="chapter.id" class="chapter-item">
              <el-checkbox :label="chapter.id">
                <span class="chapter-name">{{ chapter.name }}</span>
                <el-tag size="small" type="warning" class="chapter-wrong-count">
                  {{ getChapterWrongCount(chapter.id) }} 错题
                </el-tag>
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </div>
        <div class="shuffle-options-section">
          <el-checkbox v-model="shuffleOptionsInDialog">打乱选项顺序</el-checkbox>
        </div>
      </div>
      <template #footer>
        <el-button @click="chapterSelectVisible = false">取消</el-button>
        <el-button type="primary" @click="startPracticeWithChapters">
          <el-icon><VideoPlay /></el-icon>
          开始练习
        </el-button>
      </template>
    </el-dialog>

    <div class="card">
      <div class="filter-bar" style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; align-items: center;">
        <el-select v-model="filters.chapter_id" placeholder="选择章节" style="width: 150px;" clearable @change="loadWrongQuestions">
          <el-option v-for="ch in chapters" :key="ch.id" :label="ch.name" :value="ch.id" />
        </el-select>
        <el-select v-model="filters.question_type_id" placeholder="选择题型" style="width: 150px;" clearable @change="loadWrongQuestions">
          <el-option v-for="qt in questionTypes" :key="qt.id" :label="qt.name" :value="qt.id" />
        </el-select>
        <el-select v-model="filters.min_wrong_count" placeholder="错误次数" style="width: 130px;" clearable @change="loadWrongQuestions">
          <el-option label="全部" :value="undefined" />
          <el-option label="≥1次" :value="1" />
          <el-option label="≥2次" :value="2" />
          <el-option label="≥3次" :value="3" />
          <el-option label="≥5次" :value="5" />
        </el-select>
        <div style="flex: 1;"></div>
        <el-button v-if="selectedWrongQuestions.length > 0" type="danger" @click="batchRemove">
          <el-icon><Delete /></el-icon>
          批量移除({{ selectedWrongQuestions.length }})
        </el-button>
        <el-checkbox v-model="selectAll">全选</el-checkbox>
      </div>

      <el-table :data="wrongQuestions" style="width: 100%" v-loading="loading" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="question.id" label="ID" width="80" />
        <el-table-column prop="question.stem" label="题干" min-width="200">
          <template #default="{ row }">
            <div v-html="row.question?.stem_html || row.question?.stem"></div>
          </template>
        </el-table-column>
        <el-table-column prop="question.question_type_name" label="题型" width="100" />
        <el-table-column prop="wrong_count" label="错误次数" width="100">
          <template #default="{ row }">
            <el-tag :type="getWrongCountTagType(row.wrong_count)">{{ row.wrong_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reappearance_count" label="复现次数" width="100">
          <template #default="{ row }">
            <el-tag type="info">{{ row.reappearance_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_wrong_at" label="最近错误" width="160">
          <template #default="{ row }">
            {{ formatTime(row.last_wrong_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="practiceQuestion(row)">练习</el-button>
            <el-button size="small" type="success" @click="removeQuestion(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 20px; justify-content: center;"
        @current-change="loadWrongQuestions"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/store/quiz'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, RefreshRight, Delete } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const store = useQuizStore()

const wrongQuestions = ref([])
const chapters = ref([])
const questionTypes = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const selectedWrongQuestions = ref([])
const selectAll = ref(false)

const filters = ref({
  chapter_id: null,
  question_type_id: null,
  min_wrong_count: undefined
})

const chapterSelectVisible = ref(false)
const selectAllChapters = ref(false)
const selectedChapterIds = ref([])
const shuffleOptionsInDialog = ref(true)

const selectedChapterCount = computed(() => {
  return selectedChapterIds.value.length
})

const getChapterWrongCount = (chapterId) => {
  const chapterWrongQuestions = wrongQuestions.value.filter(wq => {
    return wq.question && wq.question.chapter_id === chapterId
  })
  return chapterWrongQuestions.length
}

const getWrongCountTagType = (count) => {
  if (count >= 5) return 'danger'
  if (count >= 3) return 'warning'
  return 'info'
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString('zh-CN')
}

const loadWrongQuestions = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value
    }
    if (filters.value.chapter_id) {
      params.chapter_id = filters.value.chapter_id
    }
    if (filters.value.question_type_id) {
      params.question_type_id = filters.value.question_type_id
    }
    if (filters.value.min_wrong_count) {
      params.min_wrong_count = filters.value.min_wrong_count
    }
    
    const result = await store.loadWrongQuestions(params)
    wrongQuestions.value = result.data
    total.value = result.total
    chapters.value = store.chapters
    questionTypes.value = store.questionTypes
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedWrongQuestions.value = selection
}

watch(selectAll, (val) => {
  if (val) {
    selectedWrongQuestions.value = [...wrongQuestions.value]
  } else {
    selectedWrongQuestions.value = []
  }
})

const showChapterSelectDialog = () => {
  selectedChapterIds.value = []
  selectAllChapters.value = false
  chapterSelectVisible.value = true
}

const handleSelectAll = (checked) => {
  if (checked) {
    selectedChapterIds.value = store.chapters.map(ch => ch.id)
  } else {
    selectedChapterIds.value = []
  }
}

const startPracticeWithChapters = async () => {
  chapterSelectVisible.value = false
  
  if (selectedChapterIds.value.length === 0) {
    ElMessage.warning('请至少选择一个章节')
    return
  }
  
  const chapterIds = selectedChapterIds.value.map(id => parseInt(id))
  const chapterIdsStr = chapterIds.join(',')
  
  router.push({
    path: '/practice/wrong',
    query: { 
      mode: 'wrong',
      chapters: chapterIdsStr,
      shuffle_options: shuffleOptionsInDialog.value ? 'true' : 'false'
    }
  })
}

const startPractice = () => {
  router.push('/practice/wrong')
}

const practiceQuestion = (row) => {
  router.push({ path: '/practice/wrong', query: { questionId: row.question_id } })
}

const removeQuestion = async (row) => {
  try {
    await store.removeFromWrongQuestions(row.id)
    ElMessage.success('已移出错题本')
    loadWrongQuestions()
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

const batchRemove = async () => {
  if (selectedWrongQuestions.value.length === 0) {
    ElMessage.warning('请先选择要移除的题目')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要移除选中的 ${selectedWrongQuestions.value.length} 道错题吗？`,
      '批量移除',
      { type: 'warning' }
    )
    
    const wrongIds = selectedWrongQuestions.value.map(wq => wq.id)
    await axios.delete('/api/wrong-questions/batch', {
      data: {
        user_id: store.userId,
        wrong_ids: wrongIds
      }
    })
    
    ElMessage.success(`已移除 ${wrongIds.length} 道错题`)
    selectAll.value = false
    selectedWrongQuestions.value = []
    loadWrongQuestions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
}

const clearAll = async () => {
  try {
    await ElMessageBox.confirm('确定要清空错题本吗？此操作不可恢复。', '警告', { type: 'warning' })
    await store.clearWrongQuestions()
    ElMessage.success('已清空')
    loadWrongQuestions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

onMounted(() => {
  loadWrongQuestions()
})
</script>

<style scoped>
.wrong-questions-view {
  padding: 20px;
}

.chapter-select-content {
  max-height: 400px;
}

.chapter-select-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.selected-count {
  font-size: 14px;
  color: #606266;
}

.chapter-list {
  max-height: 300px;
  overflow-y: auto;
}

.chapter-item {
  padding: 10px 15px;
  border-radius: 6px;
  transition: all 0.3s;
}

.chapter-item:hover {
  background: #f5f7fa;
}

.chapter-item .el-checkbox {
  width: 100%;
}

.chapter-name {
  font-size: 14px;
  color: #303133;
  margin-right: 8px;
}

.chapter-question-count {
  float: right;
}

.chapter-wrong-count {
  float: right;
}

.shuffle-options-section {
  margin-top: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
}
</style>
