// Client-side checks give the user instant feedback. The backend repeats
// every check, because anything done in the browser can be bypassed.

// Default limit; the live value comes from the backend's /api/config.
export const MAX_FILE_SIZE_MB = 5

/**
 * Returns a list of human-readable problems. An empty list means the file
 * can be sent to the backend.
 */
export function validateCsvFile(file: File | null | undefined, maxMb: number = MAX_FILE_SIZE_MB): string[] {
  if (!file) return ['Choose a CSV file to upload.']

  const errors: string[] = []
  if (!file.name.toLowerCase().endsWith('.csv')) {
    errors.push(`"${file.name}" is not a CSV file. Export your spreadsheet as .csv and try again.`)
  }
  if (file.size === 0) {
    errors.push('The file is empty.')
  } else if (file.size > maxMb * 1024 * 1024) {
    errors.push(`The file is larger than ${maxMb} MB. Upload a smaller extract of the data.`)
  }
  return errors
}
