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

// agent() 被中止或 API 出錯會回 null。交給裁決員的不是攤平的陣列——空陣列分不出
// 「檢查過、沒問題」和「沒人交報告」，所以逐一交代每個檢查員的狀態。
const checkers = [
  { 檢查員: 'check:code', 負責: 'SPEC.md 的「新指令 remove」與「測試」兩節', 結果: code },
  { 檢查員: 'check:docs', 負責: 'SPEC.md 的「文件」那一節', 結果: docs },
].map((c) => ({
  檢查員: c.檢查員,
  負責: c.負責,
  有沒有交報告: c.結果 ? '有' : '沒有（agent 被中止或出錯）',
  不符規格幾筆: c.結果 ? c.結果.findings.length : null,
  明細: c.結果 ? c.結果.findings : null,
}))

const findings = [code, docs].filter(Boolean).flatMap((r) => r.findings)
log(`Check 完成：${checkers.filter((c) => c.有沒有交報告 === '有').length}/2 個檢查員交了報告，共 ${findings.length} 筆不符規格的地方`)

phase('Verdict')
const verdict = await agent(
  '以下是出貨前檢查的結果（JSON），來自對照 SPEC.md 的兩個檢查員。' +
    '請裁決這個版本能不能出：兩個檢查員都交了報告、而且都沒有不符規格的地方，才回 go。\n\n' +
    '怎麼讀這份 JSON：\n' +
    '- 「不符規格幾筆」是 0、「明細」是空陣列 []，代表那個檢查員檢查完了、沒有發現任何不符規格的地方，' +
    '這是通過，不是「沒有報告」也不是「無從判定」。\n' +
    '- 只有「有沒有交報告」寫「沒有」時才算無從判定，那種情況回 no-go。\n\n' +
    '裁決範圍只有 SPEC.md 的「新指令 remove」「測試」「文件」三節。' +
    'SPEC.md 的「出版」那節（CHANGELOG.md 與 tag v1.0.0）是這條流程跑完之後才由 /release 產生的，' +
    '不在裁決範圍內——不要因為 CHANGELOG.md 還不存在、或還沒有 v1.0.0 這個 tag 就回 no-go。\n\n' +
    '以這份 JSON 為準做裁決，不要自己去翻 repo 重做檢查員的工作。' +
    'reasons 用繁體中文寫；有不符規格的地方就每條附 檔名:行號，判 go 就簡短說明依據。不要修改任何檔案。\n\n' +
    JSON.stringify(checkers, null, 2),
  { label: 'verdict', phase: 'Verdict', schema: VERDICT },
)

log(`Verdict：${verdict ? verdict.verdict : '裁決 agent 沒有回應'}`)

return { verdict, findings }
