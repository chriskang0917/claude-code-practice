// ship-check：出貨前對照 SPEC.md 檢查兩邊，再由第三個 agent 裁決 go／no-go。
// 放到 .claude/workflows/ship-check.js，/exit 重開 claude 後用 /ship-check 執行。
export const meta = {
  name: 'ship-check',
  description: '對照 SPEC.md 平行檢查程式與文件，再裁決能不能出版',
  phases: [{ title: 'Check' }, { title: 'Verdict' }],
}

// 兩個檢查 agent 都必須回這個形狀：findings[] 每筆帶 file / line / note
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

// 裁決 agent 只能回 go 或 no-go，不能自由發揮
const VERDICT = {
  type: 'object',
  required: ['verdict', 'reasons'],
  properties: {
    verdict: { type: 'string', enum: ['go', 'no-go'] },
    reasons: { type: 'array', items: { type: 'string' } },
  },
}

// prompt 要自足：subagent 看不到主對話，要讀哪些檔、對照什麼、回什麼形狀都得寫在這裡
const checkPrompt = (files, focus) =>
  `你是唯讀的出貨前檢查員。用 Read 工具讀取 SPEC.md，再讀取 ${files}，` +
  `逐條對照 SPEC.md 裡${focus}的要求，找出沒做到或做得跟規格不一樣的地方。` +
  `每筆都要附行號（line 為整數）。最多 5 筆；完全符合就回空陣列。不要修改任何檔案。`

phase('Check')
const [code, docs] = await parallel([
  () =>
    agent(checkPrompt('src/todo.py 與 tests/test_todo.py', '「新指令 remove」與「測試」兩節'), {
      label: 'check:code',
      phase: 'Check',
      schema: FINDINGS,
    }),
  () =>
    agent(checkPrompt('README.md', '「文件」那一節'), {
      label: 'check:docs',
      phase: 'Check',
      schema: FINDINGS,
    }),
])

// agent() 被中止或 API 出錯會回 null，先濾掉再彙整
const findings = [code, docs].filter(Boolean).flatMap((r) => r.findings)
log(`Check 完成：共 ${findings.length} 筆不符規格的地方`)

phase('Verdict')
const verdict = await agent(
  '以下是出貨前檢查的結果（JSON），來自對照 SPEC.md 的兩個檢查員。' +
    '請裁決這個版本能不能出：完全沒有不符規格的地方才回 go，否則回 no-go。' +
    'reasons 用繁體中文寫，每條附 檔名:行號。不要修改任何檔案。\n\n' +
    JSON.stringify(findings, null, 2),
  { label: 'verdict', phase: 'Verdict', schema: VERDICT },
)

log(`Verdict：${verdict ? verdict.verdict : '裁決 agent 沒有回應'}`)

return { verdict, findings }
