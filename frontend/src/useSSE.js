import { ref } from 'vue'

export function useSSE() {
  const isOptimizing = ref(false)
  const steps = ref([])
  const improvedPrompt = ref('')
  const sessionId = ref('') // 存储当前会话 ID
  const promptVersions = ref([]) // 存储所有版本的提示词
  const error = ref('')

  const optimize = async (originalPrompt) => {
    isOptimizing.value = true
    steps.value = []
    improvedPrompt.value = ''
    sessionId.value = ''
    promptVersions.value = []
    error.value = ''

    try {
      const apiBase = `${window.location.protocol}//${window.location.hostname}:8000`
      const response = await fetch(`${apiBase}/api/optimize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: originalPrompt }),
      })

      if (!response.ok) throw new Error('网络请求失败')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6)
            if (content === '[DONE]') {
              isOptimizing.value = false
              continue
            }

            try {
              const data = JSON.parse(content)
              handleEvent(data)
            } catch (e) {
              console.error('解析 SSE 数据失败', e)
            }
          }
        }
      }
    } catch (err) {
      error.value = err.message
      isOptimizing.value = false
    }
  }

  const handleEvent = (data) => {
    const { node, status, updates, session_id } = data
    
    // 处理初始化事件
    if (status === 'init') {
      sessionId.value = session_id
      return
    }

    const stepNameMap = {
      'analyzer': '意图分析',
      'generator': '提示词优化',
      'reflector': '自我反思与评审'
    }

    if (!stepNameMap[node]) return

    if (status === 'start') {
      // 检查当前节点是否是 generator 的迭代
      const isIteration = node === 'generator' && steps.value.some(s => s.node === 'generator')
      const roundNum = isIteration ? steps.value.filter(s => s.node === 'generator').length + 1 : 1

      // 如果是 generator 开始执行，清除之前的旧内容准备接收新流
      if (node === 'generator') {
        improvedPrompt.value = ''
        // 创建一个占位版本，后续通过 token 更新
        const roundNum = steps.value.filter(s => s.node === 'generator').length + 1
        promptVersions.value.push({
          version: roundNum,
          content: '',
          time: new Date().toLocaleTimeString()
        })
      }
      
      steps.value.push({
        node,
        name: node === 'generator' ? `${stepNameMap[node]} (第${roundNum}轮)` : stepNameMap[node],
        status: 'process',
        statusText: node === 'analyzer' || node === 'reflector' ? '等待中...' : '准备输出...',
        time: new Date().toLocaleTimeString()
      })
    } else if (status === 'end') {
      // 标记该节点为完成
      const step = steps.value.find(s => s.node === node && s.status === 'process')
      if (step) {
        step.status = 'success'
        step.statusText = '已完成'
        // 如果有 RAG 匹配信息，保存到步骤中
        if (updates && updates.rag_match) {
          step.ragMatch = updates.rag_match
        }
      }

      // 更新最终结果
      if (updates && updates.improved_prompt) {
        if (!improvedPrompt.value) {
          improvedPrompt.value = updates.improved_prompt
        }
        // 同步更新对应的版本内容
        const roundNum = steps.value.filter(s => s.node === 'generator').length
        const versionObj = promptVersions.value.find(v => v.version === roundNum)
        if (versionObj) {
          versionObj.content = updates.improved_prompt
        }
      }
    } else if (status === 'token') {
      if (node === 'generator') {
        const step = steps.value.find(s => s.node === node && s.status === 'process')
        if (step) {
          step.statusText = '正在输出...'
        }
        improvedPrompt.value += data.token
        // 实时更新当前版本的内容
        const currentVersion = promptVersions.value[promptVersions.value.length - 1]
        if (currentVersion) {
          currentVersion.content += data.token
        }
      }
    }
  }

  return {
    isOptimizing,
    steps,
    improvedPrompt,
    sessionId,
    promptVersions,
    error,
    optimize
  }
}
