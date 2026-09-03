// ship-check：出版前驗收——平行對照「程式 vs SPEC.md」與「文件 vs SPEC.md」，再由第三個 agent 給 go / no-go。
// 放到 .claude/workflows/ship-check.js，/exit 重開 claude 後用 /ship-check 執行。
export const meta = {
  name: 'ship-check',
  description: '出版前驗收：程式與文件都對照 SPEC.md，給 go/no-go',
  phases: [{ title: 'Check' }, { title: 'Verdict' }],
}

// Check 站每個 agent 都回這個形狀：findings[] 每筆帶 file / line / note
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

// Verdict 站回這個形狀：verdict 只能是 go 或 no-go
const VERDICT = {
  type: 'object',
  required: ['verdict', 'reasons'],
  properties: {
    verdict: { type: 'string', enum: ['go', 'no-go'] },
    reasons: { type: 'array', items: { type: 'string' } },
  },
}

// prompt 要自足：subagent 看不到主對話，要讀哪些檔、對照什麼、回什麼都寫在這裡
const checkPrompt = (what, files) =>
  `你是唯讀的驗收員。先用 Read 讀 SPEC.md，再讀 ${files}，找出${what}與 SPEC.md 不一致的地方。` +
  `每筆都要附 file 與 line（整數）。最多 5 筆；完全一致就回空陣列。不要修改任何檔案。`

phase('Check')
const [code, docs] = await parallel([
  () => agent(checkPrompt('程式行為', 'src/todo.py 與 tests/test_todo.py'), { label: 'check:code', phase: 'Check', schema: FINDINGS }),
  () => agent(checkPrompt('文件描述', 'README.md'), { label: 'check:docs', phase: 'Check', schema: FINDINGS }),
])

// agent() 被中止或 API 出錯會回 null，先濾掉再彙整
const findings = [code, docs].filter(Boolean).flatMap((r) => r.findings)
log(`Check 完成：共 ${findings.length} 筆不一致`)

phase('Verdict')
const verdict = await agent(
  '以下是出版前驗收找到的不一致清單（JSON）。清單為空、或只有不影響使用者的小問題，verdict 給 go；' +
    '否則給 no-go。reasons 用繁體中文，每條附 檔名:行號。不要修改任何檔案。\n\n' +
    JSON.stringify(findings, null, 2),
  { label: 'verdict', phase: 'Verdict', schema: VERDICT },
)
log(`Verdict：${verdict ? verdict.verdict : 'agent 失敗'}`)

return verdict
