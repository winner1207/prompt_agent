<template>
  <div class="app-container">
    <el-container>
      <el-header class="header">
        <div class="logo">
          <img src="/favicon.svg" alt="Logo" class="logo-img" />
          <span>易景Prompt智能助手</span>
        </div>
      </el-header>

      <el-main class="main-content">
        <el-row :gutter="20">
          <!-- 左侧输入区：缩减宽度 -->
          <el-col :span="8">
            <el-card class="box-card">
              <template #header>
                <div class="card-header">
                  <span>原始想法 (Rough Idea)</span>
                </div>
              </template>
              <el-input
                v-model="originalPrompt"
                type="textarea"
                :rows="12"
                placeholder="在此输入您的模糊想法，我将为您深度优化为专业的结构化提示词... (Ctrl+Enter 发送)"
                :disabled="isOptimizing"
                @keydown.ctrl.enter="handleOptimize"
              />
              <div class="action-bar">
                <el-button 
                  type="primary" 
                  size="large" 
                  :loading="isOptimizing"
                  @click="handleOptimize"
                  icon="Promotion"
                >
                  开始优化
                </el-button>
              </div>
            </el-card>
          </el-col>

          <!-- 中间过程区：相应增加宽度 -->
          <el-col :span="6">
            <el-card class="box-card process-card">
              <template #header>
                <div class="card-header">
                  <span>Agent 思考过程</span>
                </div>
              </template>
              <el-timeline v-if="steps.length > 0">
                <el-timeline-item
                  v-for="(step, index) in steps"
                  :key="index"
                  :timestamp="step.time"
                  :type="step.status === 'process' ? 'primary' : 'success'"
                  :hollow="step.status === 'process'"
                  :color="step.ragMatch ? '#722ed1' : ''"
                  :icon="step.ragMatch ? 'Collection' : ''"
                  size="large"
                >
                  <div class="step-content">
                    <span class="step-name">{{ step.name }}</span>
                    <div class="step-meta">
                      <span class="step-status">{{ step.statusText }}</span>
                    </div>
                    <!-- 独立的知识卡片 -->
                    <transition name="fade-slide">
                      <div v-if="step.ragMatch" class="knowledge-card">
                        <div class="knowledge-header">
                          <el-icon class="knowledge-icon"><Reading /></el-icon>
                          <span>企业知识库已介入</span>
                        </div>
                        <div class="knowledge-body">
                          <span class="knowledge-label">匹配意图:</span>
                          <span class="knowledge-value">{{ step.ragMatch }}</span>
                        </div>
                      </div>
                    </transition>
                  </div>
                </el-timeline-item>
              </el-timeline>
              <el-empty v-else description="等待开始..." :image-size="60" />
            </el-card>
          </el-col>

          <!-- 右侧输出区 -->
          <el-col :span="10">
            <el-card class="box-card">
              <template #header>
                <div class="card-header">
                  <span>优化后的提示词 (Structured Prompt)</span>
                  <div class="header-actions">
                    <el-checkbox v-if="promptVersions.length > 1" v-model="showDiff" label="显示差异" class="diff-toggle" />
                    <el-button 
                      v-if="improvedPrompt || promptVersions.length > 0" 
                      type="warning" 
                      size="small" 
                      icon="Star"
                      :loading="isSaving"
                      @click="saveToLibrary"
                    >
                      收藏
                    </el-button>
                    <el-button 
                      v-if="improvedPrompt || promptVersions.length > 0" 
                      type="success" 
                      size="small" 
                      icon="DocumentCopy"
                      :disabled="isOptimizing"
                      @click="copyResult"
                    >
                      复制
                    </el-button>
                  </div>
                </div>
              </template>
              <div class="result-area">
                <div v-if="isOptimizing && promptVersions.length === 0" class="loading-container">
                  <el-skeleton :rows="10" animated />
                  <div class="loading-text">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    AI 正在深度思考并构思提示词...
                  </div>
                </div>
                <div v-else-if="promptVersions.length > 0">
                  <el-tabs v-model="activeVersion" class="version-tabs">
                    <el-tab-pane 
                      v-for="(v, idx) in promptVersions" 
                      :key="idx" 
                      :label="'版本 v' + v.version" 
                      :name="idx"
                    >
                      <div v-if="showDiff && idx > 0" class="diff-view" v-html="renderDiff(v.content, promptVersions[idx-1].content)"></div>
                      <div v-else class="markdown-body" v-html="renderMarkdown(v.content)"></div>
                    </el-tab-pane>
                  </el-tabs>
                </div>
                <el-empty v-else description="暂无结果" />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useSSE } from './useSSE'
import MarkdownIt from 'markdown-it'
import { ElMessage } from 'element-plus'
import { diff_match_patch } from 'diff-match-patch'

const md = new MarkdownIt()
const dmp = new diff_match_patch()
const originalPrompt = ref('输入您的原始想法（例如：写代码、写文案或做策划），我将通过“意图分析 -> 提示词生成 -> 专家评审”流程，为您打造高质量的结构化 Prompt。')
const { isOptimizing, steps, improvedPrompt, sessionId, promptVersions, error, optimize } = useSSE()

const activeVersion = ref(0)
const isSaving = ref(false)
const showDiff = ref(false)

// 渲染 Markdown
const renderMarkdown = (content) => {
  return md.render(content || '')
}

// 计算差异
const renderDiff = (currentContent, previousContent) => {
  if (!previousContent) return renderMarkdown(currentContent)
  const diffs = dmp.diff_main(previousContent, currentContent)
  dmp.diff_cleanupSemantic(diffs)
  return dmp.diff_prettyHtml(diffs)
}

const renderedPrompt = computed(() => {
  return md.render(improvedPrompt.value)
})

// 监听 promptVersions 变化，如果是第一轮开始，重置 activeVersion
watch(promptVersions, (newVal) => {
  if (newVal.length > 0) {
    // 始终切到最新的版本
    activeVersion.value = newVal.length - 1
  }
}, { deep: true })

const handleOptimize = () => {
  if (!originalPrompt.value.trim()) {
    ElMessage.warning('请输入内容')
    return
  }
  activeVersion.value = 0
  optimize(originalPrompt.value)
}

const copyResult = () => {
  const content = promptVersions.value[activeVersion.value]?.content || improvedPrompt.value
  navigator.clipboard.writeText(content)
  ElMessage.success('已复制到剪贴板')
}

// 收藏到个人库
const saveToLibrary = async () => {
  const currentContent = promptVersions.value[activeVersion.value]?.content || improvedPrompt.value
  if (!currentContent) return

  isSaving.value = true
  try {
    const apiBase = `${window.location.protocol}//${window.location.hostname}:8000`
    const response = await fetch(`${apiBase}/api/save_prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: originalPrompt.value.substring(0, 20) + (originalPrompt.value.length > 20 ? '...' : ''),
        content: currentContent,
        session_id: sessionId.value,
        tags: 'AI优化'
      })
    })
    const data = await response.json()
    if (data.success) {
      ElMessage.success('已存入个人提示词库')
    } else {
      ElMessage.error(data.message)
    }
  } catch (err) {
    ElMessage.error('保存失败，请检查网络')
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  background-color: #f5f7fa;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: #409eff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-img {
  width: 32px;
  height: 32px;
  border-radius: 6px;
}

.main-content {
  padding: 20px;
}

.box-card {
  height: auto;
  overflow: visible;
}

.process-card {
  overflow-y: auto;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-name {
  font-weight: bold;
  font-size: 14px;
}

.step-meta {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
  flex-wrap: wrap;
}

.step-status {
  white-space: nowrap;
}

/* 知识卡片样式 */
.knowledge-card {
  margin-top: 8px;
  background: linear-gradient(135deg, #f9f0ff 0%, #ffffff 100%);
  border: 1px solid #d3adf7;
  border-radius: 6px;
  padding: 8px 12px;
  box-shadow: 0 2px 4px rgba(114, 46, 209, 0.05);
  position: relative;
  overflow: hidden;
}

.knowledge-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background-color: #722ed1;
}

.knowledge-header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #722ed1;
  font-weight: bold;
  font-size: 12px;
  margin-bottom: 4px;
}

.knowledge-icon {
  font-size: 14px;
}

.knowledge-body {
  font-size: 12px;
  display: flex;
  gap: 6px;
}

.knowledge-label {
  color: #8c8c8c;
}

.knowledge-value {
  color: #595959;
  font-weight: 500;
}

/* 动画效果 */
.fade-slide-enter-active {
  transition: all 0.4s ease-out;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.step-time {
  opacity: 0.8;
}

.loading-container {
  padding: 20px;
}

.loading-text {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #409eff;
  font-size: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.diff-toggle {
  margin-right: 8px;
  font-weight: normal;
}

.version-tabs {
  margin-top: -10px;
}

:deep(.el-tabs__header) {
  margin-bottom: 15px;
}

.action-bar {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.result-area {
  height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 10px;
  background: #fff;
  border-radius: 4px;
}

.diff-view {
  font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  padding: 10px;
  background: #fdfdfd;
  border: 1px dashed #e1e4e8;
  border-radius: 4px;
}

:deep(.diff-view ins) {
  background-color: #e6ffed;
  color: #22863a;
  text-decoration: none;
  font-weight: bold;
}

:deep(.diff-view del) {
  background-color: #ffeef0;
  color: #cb2431;
  text-decoration: line-through;
}

/* Markdown 样式微调 */
:deep(.markdown-body) {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
}

:deep(.markdown-body h1, .markdown-body h2, .markdown-body h3) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
}

:deep(.markdown-body pre) {
  background-color: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow: auto;
}
</style>
