export interface LearningBlock { kind: 'heading' | 'text' | 'code'; text: string }
// Render only text nodes; raw HTML and links are never executed.
export function learningBlocks(content: string): LearningBlock[] {
  const blocks: LearningBlock[] = []
  let code: string[] | null = null
  for (const line of content.split('\n')) {
    if (/^```/.test(line)) {
      if (code) { blocks.push({ kind: 'code', text: code.join('\n') }); code = null }
      else code = []
    } else if (code) code.push(line)
    else if (/^#{1,6}\s/.test(line)) blocks.push({ kind: 'heading', text: line.replace(/^#{1,6}\s+/, '') })
    else if (line.trim()) blocks.push({ kind: 'text', text: line.replace(/^[-*]\s/, '• ') })
  }
  if (code) blocks.push({ kind: 'code', text: code.join('\n') })
  return blocks
}
