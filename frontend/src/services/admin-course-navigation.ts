export function adminResourceId(value:unknown):number|undefined {
  const text=String(value??'')
  const id=Number(text)
  return /^[1-9]\d*$/.test(text) && Number.isSafeInteger(id) ? id : undefined
}
