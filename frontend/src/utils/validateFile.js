// Client-side checks give the user instant feedback. The backend repeats
// every check (Stage 3), because anything done in the browser can be bypassed.

export const MAX_FILE_SIZE_MB = 5
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

/**
 * Returns a list of human-readable problems. An empty list means the file
 * can be sent to the backend.
 */
export function validateCsvFile(file) {
  if (!file) return ['Choose a CSV file to upload.']

  const errors = []
  if (!file.name.toLowerCase().endsWith('.csv')) {
    errors.push(`"${file.name}" is not a CSV file. Export your spreadsheet as .csv and try again.`)
  }
  if (file.size === 0) {
    errors.push('The file is empty.')
  } else if (file.size > MAX_FILE_SIZE_BYTES) {
    errors.push(`The file is larger than ${MAX_FILE_SIZE_MB} MB. Upload a smaller extract of the data.`)
  }
  return errors
}
