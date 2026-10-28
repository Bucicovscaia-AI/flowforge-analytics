import { ShieldCheck } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

export const BEFORE_YOU_UPLOAD_ID = 'before-you-upload'

const HABITS = [
  {
    title: 'Use demo or anonymised data only',
    text: 'The public demo has no login, so anyone with the link could see what you upload. Remove names, emails and phone numbers first.',
  },
  {
    title: 'Keep the webhook address private',
    text: 'The Make.com webhook URL works like a password. Never paste it into chats, tickets or screenshots.',
  },
  {
    title: 'Check before you forward',
    text: 'Look at the quality score and date range first. Forward the PDF file, never the download link, and only to people who need it.',
  },
]

/** Security habits shown at the moment of upload. Settings links here with #before-you-upload. */
export function BeforeYouUploadCard() {
  const ref = useRef<HTMLElement>(null)
  const { hash } = useLocation()

  useEffect(() => {
    if (hash === `#${BEFORE_YOU_UPLOAD_ID}`) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [hash])

  return (
    <section
      ref={ref}
      id={BEFORE_YOU_UPLOAD_ID}
      aria-labelledby={`${BEFORE_YOU_UPLOAD_ID}-title`}
      className="min-w-0 scroll-mt-24 overflow-hidden rounded-xl border border-brand-900/20 bg-white shadow-card"
    >
      <div className="flex items-start gap-3 bg-brand-900 px-5 py-4 text-white">
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-brand-200" aria-hidden />
        <div className="min-w-0">
          <h2 id={`${BEFORE_YOU_UPLOAD_ID}-title`} className="text-base font-semibold">
            Before you upload
          </h2>
          <p className="mt-0.5 text-sm text-brand-100">Three habits that keep your data and your reports safe</p>
        </div>
      </div>
      <ol className="divide-y divide-slate-100">
        {HABITS.map((habit, index) => (
          <li key={habit.title} className="flex gap-4 px-5 py-4">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-amber-500 text-sm font-bold text-white" aria-hidden>
              {index + 1}
            </span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-brand-900">{habit.title}</h3>
              <p className="mt-0.5 text-sm leading-relaxed text-slate-600">{habit.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
