import { formatBytes } from './format'

/** Checks that can be made before sending a file. The server repeats every check. */
export function validateFileLocally(file: File, maxMb: number): string | null {
  const name = file.name.toLowerCase()
  if (!name.endsWith('.csv') && !name.endsWith('.txt')) return 'Only CSV files (.csv) are supported.'
  if (file.size === 0) return 'The file is empty.'
  if (file.size > maxMb * 1024 * 1024) return `The file is ${formatBytes(file.size)}; the limit is ${maxMb} MB.`
  return null
}
