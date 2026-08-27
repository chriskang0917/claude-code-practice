// review-flow：平行審兩個檔，再把 findings 彙整成一段 zh-TW 摘要。
// 放到 .claude/workflows/review-flow.js，/exit 重開 claude 後用 /review-flow 執行。
export const meta = {
  name: 'review-flow',
  description: '平行審兩個檔再彙整',
  phases: [{ title: 'Review' }, { title: 'Synthesize' }],
}

// 每個審查 agent 都必須回這個形狀：findings[] 每筆帶 file / line / note
const FINDINGS = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'line', 'note'],
        properties: { file: { type: 'string' }, line: { type: 'integer' }, note: { type: 'string' } },
      },
    },
  },
}

// prompt 要自足：subagent 看不到主對話，檔名、要看什麼、回什麼都得寫在這裡
const reviewPrompt = (file) =>
  `你是唯讀的程式碼審查員。用 Read 工具讀取 ${file}，找出可讀性、錯誤處理、測試涵蓋上的問題。` +
  `每筆都要附行號（line 為整數）。最多 5 筆；沒有問題就回空陣列。不要修改任何檔案。`

phase('Review')
const [todo, tests] = await parallel([
  () => agent(reviewPrompt('src/todo.py'), { label: 'review:todo', phase: 'Review', schema: FINDINGS }),
  () => agent(reviewPrompt('tests/test_todo.py'), { label: 'review:tests', phase: 'Review', schema: FINDINGS }),
])

// agent() 被中止或 API 出錯會回 null，先濾掉再彙整
const findings = [todo, tests].filter(Boolean).flatMap((r) => r.findings)
log(`Review 完成：共 ${findings.length} 筆 findings`)

phase('Synthesize')
const summary = await agent(
  '以下是兩個檔案的程式碼審查結果（JSON）。請用繁體中文寫一段 150 字以內的摘要：' +
    '先講整體狀況，再列最值得先處理的 3 點（每點附 檔名:行號）。不要修改任何檔案，直接回摘要文字。\n\n' +
    JSON.stringify(findings, null, 2),
  { label: 'synthesize', phase: 'Synthesize' },
)

return summary
