import { defineStore } from 'pinia'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

export const useQuizStore = defineStore('quiz', {
  state: () => ({
    chapters: [],
    questionTypes: [],
    questions: [],
    wrongQuestions: [],
    favoriteQuestions: [],
    preferences: {
      eye_protection_mode: 'none',
      font_size: 16,
      font_family: 'Microsoft YaHei'
    },
    currentSession: null,
    userId: 'default_user',
    statistics: {
      total_questions: 0,
      total_answered: 0,
      total_correct: 0,
      correct_rate: 0,
      wrong_count: 0,
      favorite_count: 0
    },
    // 保存的刷题进程
    savedPracticeSessions: {}
  }),

  actions: {
    async initDatabase() {
      try {
        await api.post('/init-db')
        await this.loadChapters()
        await this.loadQuestionTypes()
        await this.loadPreferences()
      } catch (error) {
        console.error('Failed to initialize database:', error)
      }
    },

    async loadChapters() {
      const res = await api.get('/chapters')
      this.chapters = res.data.data || []
    },

    async createChapter(data) {
      const res = await api.post('/chapters', data)
      await this.loadChapters()
      return res.data.data
    },

    async updateChapter(id, data) {
      const res = await api.put(`/chapters/${id}`, data)
      await this.loadChapters()
      return res.data.data
    },

    async deleteChapter(id) {
      await api.delete(`/chapters/${id}`)
      await this.loadChapters()
    },

    async loadQuestionTypes() {
      const res = await api.get('/question-types')
      this.questionTypes = res.data.data || []
    },

    async createQuestionType(data) {
      const res = await api.post('/question-types', data)
      await this.loadQuestionTypes()
      return res.data.data
    },

    async updateQuestionType(id, data) {
      const res = await api.put(`/question-types/${id}`, data)
      await this.loadQuestionTypes()
      return res.data.data
    },

    async deleteQuestionType(id) {
      await api.delete(`/question-types/${id}`)
      await this.loadQuestionTypes()
    },

    async loadQuestions(params = {}) {
      const res = await api.get('/questions', { params })
      this.questions = res.data.data || []
      return res.data
    },

    async createQuestion(data) {
      const res = await api.post('/questions', data)
      return res.data.data
    },

    async updateQuestion(id, data) {
      const res = await api.put(`/questions/${id}`, data)
      return res.data.data
    },

    async deleteQuestion(id) {
      await api.delete(`/questions/${id}`)
    },

    async batchOperateQuestions(data) {
      const res = await api.post('/questions/batch', data)
      return res.data
    },

    async uploadQuestions(file, duplicateHandling = 'skip') {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('duplicate_handling', duplicateHandling)
      const res = await api.post('/import/upload', formData)
      return res.data
    },

    async downloadTemplate() {
      const res = await api.get('/import/template', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'question_template.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
    },

    async exportQuestions(questionIds = []) {
      const res = await api.post('/export/questions', { question_ids: questionIds }, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'exported_questions.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
    },

    async practiceMemorize(params = {}) {
      const res = await api.get('/practice/memorize', { params })
      return res.data
    },

    async practiceRandom(data) {
      const res = await api.post('/practice/random', data)
      this.currentSession = res.data.session_id
      return res.data
    },

    async practiceSequential(data) {
      const res = await api.post('/practice/sequential', data)
      this.currentSession = res.data.session_id
      return res.data
    },

    async loadWrongQuestions(params = {}) {
      params.user_id = this.userId
      const res = await api.get('/wrong-questions', { params })
      this.wrongQuestions = res.data.data || []
      return res.data
    },

    async addToWrongQuestions(questionId) {
      const res = await api.post('/wrong-questions', {
        question_id: questionId,
        user_id: this.userId
      })
      return res.data.data
    },

    async removeFromWrongQuestions(wrongId) {
      await api.delete(`/wrong-questions/${wrongId}`)
      await this.loadWrongQuestions()
    },

    async clearWrongQuestions() {
      await api.delete(`/wrong-questions/clear?user_id=${this.userId}`)
      await this.loadWrongQuestions()
    },

    async practiceWrongQuestions(shuffle = true) {
      const res = await api.post('/wrong-questions/practice', {
        user_id: this.userId,
        shuffle
      })
      this.currentSession = {
        id: res.data.session_id,
        type: 'wrong_questions',
        chapter_ids: []
      }
      return res.data
    },

    async practiceWrongQuestionsByChapter(data) {
      const res = await api.post('/wrong-questions/practice', {
        user_id: this.userId,
        shuffle: data.shuffle,
        chapter_ids: data.chapter_ids
      })
      this.currentSession = {
        id: res.data.session_id,
        type: 'wrong_questions_by_chapter',
        chapter_ids: data.chapter_ids
      }
      return res.data
    },

    async loadFavorites(params = {}) {
      params.user_id = this.userId
      const res = await api.get('/favorites', { params })
      this.favoriteQuestions = res.data.data || []
      return res.data
    },

    async addToFavorites(questionId) {
      const res = await api.post('/favorites', {
        question_id: questionId,
        user_id: this.userId
      })
      return res.data.data
    },

    async removeFromFavorites(favoriteId) {
      await api.delete(`/favorites/${favoriteId}`)
      await this.loadFavorites()
    },

    async checkFavorite(questionId) {
      const res = await api.get(`/favorites/check/${questionId}?user_id=${this.userId}`)
      return res.data.is_favorite
    },

    async submitAnswer(questionId, userAnswer) {
      const session_id = typeof this.currentSession === 'object' ? this.currentSession.id : this.currentSession
      const res = await api.post('/answers', {
        session_id: session_id || this.userId,
        question_id: questionId,
        answer: userAnswer,
        user_id: this.userId
      })
      return res.data.data
    },

    async getAnswerHistory(questionId) {
      const res = await api.get(`/answers/history/${questionId}?user_id=${this.userId}`)
      return res.data.data
    },

    async loadPreferences() {
      const res = await api.get(`/preferences?user_id=${this.userId}`)
      this.preferences = res.data.data
      this.applyPreferences()
    },

    async updatePreferences(data) {
      const res = await api.put(`/preferences?user_id=${this.userId}`, data)
      this.preferences = res.data.data
      this.applyPreferences()
      return res.data.data
    },

    applyPreferences() {
      const { eye_protection_mode, font_size, font_family } = this.preferences
      document.documentElement.style.setProperty('--font-size-base', `${font_size}px`)
      document.documentElement.style.setProperty('--font-family-base', font_family)

      document.body.classList.remove('eye-protection-warm', 'eye-protection-light', 'eye-protection-dark')
      if (eye_protection_mode !== 'none') {
        document.body.classList.add(`eye-protection-${eye_protection_mode}`)
      }
    },

    async loadStatistics() {
      const res = await api.get(`/statistics?user_id=${this.userId}`)
      this.statistics = res.data.data
      return res.data.data
    },

    // 保存刷题进程
    savePracticeSession(practiceMode, sessionData) {
      this.savedPracticeSessions[practiceMode] = {
        ...sessionData,
        savedAt: Date.now()
      }
      // 保存到localStorage
      localStorage.setItem('savedPracticeSessions', JSON.stringify(this.savedPracticeSessions))
    },

    // 获取保存的刷题进程
    getSavedPracticeSession(practiceMode) {
      // 先从localStorage加载
      const saved = localStorage.getItem('savedPracticeSessions')
      if (saved) {
        this.savedPracticeSessions = JSON.parse(saved)
      }
      return this.savedPracticeSessions[practiceMode]
    },

    // 删除保存的刷题进程
    clearSavedPracticeSession(practiceMode) {
      delete this.savedPracticeSessions[practiceMode]
      localStorage.setItem('savedPracticeSessions', JSON.stringify(this.savedPracticeSessions))
    },

    // 检查是否有正在进行的刷题进程
    hasOngoingPractice(excludeMode = null) {
      const saved = localStorage.getItem('savedPracticeSessions')
      if (!saved) return false
      
      const sessions = JSON.parse(saved)
      for (const mode in sessions) {
        if (excludeMode && mode === excludeMode) continue
        if (sessions[mode] && sessions[mode].practiceStarted) {
          return true
        }
      }
      return false
    }
  }
})
