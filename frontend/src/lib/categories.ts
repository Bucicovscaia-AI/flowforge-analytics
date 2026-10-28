/** Same normalisation as the backend's inconsistent-category check: trim, collapse spaces, ignore case. */
export function categoryKey(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLocaleLowerCase()
}

/** Groups of labels that differ only in capitalisation or spacing, such as "Electronics" and "electronics". */
export function categoryVariants(labels: string[]): string[][] {
  const groups = new Map<string, string[]>()
  for (const label of labels) {
    const key = categoryKey(label)
    if (!key) continue
    groups.set(key, [...(groups.get(key) ?? []), label])
  }
  return [...groups.values()].filter((group) => group.length > 1)
}

/**
 * A note for charts whose groups contain such variants. The values are charted as stored; merging them is
 * left to the explicit, recorded "Normalise text" operation on the Data Quality page.
 */
export function categoryVariantNote(labels: string[]): string | undefined {
  const variants = categoryVariants(labels)
  if (!variants.length) return undefined
  const examples = variants
    .slice(0, 2)
    .map((group) => group.map((label) => `'${label}'`).join(' and '))
    .join('; ')
  return `${examples} differ only in capitalisation or spacing and are shown as separate groups. Use Normalise text on the Data Quality page to combine them.`
}
