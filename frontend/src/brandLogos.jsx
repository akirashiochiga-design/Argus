/** Logos de marques — PNG officiels dans /public/logos, fallback SVG. */

const PNG_SLUGS = new Set([
  'gmail',
  'outlook',
  'slack',
  'teams',
  'whatsapp_business',
  'whatsapp',
  'google_drive',
  'drive',
  'onedrive',
  'notion',
  'sharepoint',
  'coresinistre',
  'insurance_core',
  'erp',
  'erp_interne_demo',
  'digiclaim',
  'micard',
  'pass',
  'proassur',
  'erecours',
])

const PNG_FILE = {
  whatsapp: 'whatsapp_business',
  drive: 'google_drive',
  insurance_core: 'coresinistre',
  erp_interne_demo: 'erp',
}

const wrap = (children, className = '') => (
  <svg viewBox="0 0 24 24" className={`h-full w-full ${className}`} aria-hidden="true">
    {children}
  </svg>
)

export function BrandLogo({ slug, className = '' }) {
  const c = className
  switch (slug) {
    case 'gmail':
      return wrap(
        <>
          <path fill="#EA4335" d="M3 5.5v13A1.5 1.5 0 0 0 4.5 20H6V10.8l6 4.5 6-4.5V20h1.5A1.5 1.5 0 0 0 21 18.5v-13L12 12 3 5.5Z" />
          <path fill="#34A853" d="M3 5.5 12 12V20H6V10.8L3 8.55V5.5Z" opacity=".35" />
          <path fill="#4285F4" d="M21 5.5v3.05L18 10.8V20h1.5A1.5 1.5 0 0 0 21 18.5v-13Z" />
          <path fill="#FBBC05" d="M3 5.5 12 12l9-6.5H3Z" opacity=".9" />
          <path fill="#C5221F" d="M12 12 3 5.5h18L12 12Z" />
        </>,
        c,
      )
    case 'outlook':
      return wrap(
        <>
          <rect x="2" y="5" width="13" height="14" rx="1.5" fill="#0078D4" />
          <path fill="#28A8EA" d="M4 7.2 8.5 10.5 13 7.2V17H4V7.2Z" opacity=".85" />
          <circle cx="17.5" cy="12" r="4.5" fill="#0A66C2" />
          <path fill="#fff" d="M15.4 10.2h1.3c.9 0 1.5.5 1.5 1.3 0 .6-.3 1-.8 1.2l1 1.8h-1.2l-.85-1.6H16.6v1.6h-1.2v-4.3Zm1.25 1.85c.35 0 .55-.2.55-.45s-.2-.45-.55-.45h-.9v.9h.9Z" />
        </>,
        c,
      )
    case 'slack':
      return wrap(
        <>
          <path fill="#E01E5A" d="M8.1 14.6a1.55 1.55 0 1 1-1.55-1.55h1.55v1.55Zm.78 0A1.55 1.55 0 1 1 10.43 16.15V14.6H8.88Z" />
          <path fill="#36C5F0" d="M9.66 8.1A1.55 1.55 0 1 1 11.2 6.55V8.1H9.66Zm0 .78A1.55 1.55 0 1 1 8.11 10.43H9.66V8.88Z" />
          <path fill="#2EB67D" d="M15.9 9.4a1.55 1.55 0 1 1 1.55 1.55H15.9V9.4Zm-.78 0A1.55 1.55 0 1 1 13.57 7.85V9.4h1.55Z" />
          <path fill="#ECB22E" d="M14.34 15.9a1.55 1.55 0 1 1-1.55 1.55V15.9h1.55Zm0-.78A1.55 1.55 0 1 1 15.89 13.57H14.34v1.55Z" />
        </>,
        c,
      )
    case 'teams':
      return wrap(
        <>
          <circle cx="16.2" cy="7.2" r="2.2" fill="#5059C9" />
          <ellipse cx="16.4" cy="13.2" rx="4.2" ry="3.4" fill="#7B83EB" />
          <rect x="3.5" y="8" width="10" height="11" rx="1.4" fill="#4B53BC" />
          <path fill="#fff" d="M6.2 11.2h1.35l1.35 3.5 1.35-3.5H11.6v5.1h-1.15v-3.55l-1.25 3.55H8.05L6.8 12.75v3.55H5.65v-5.1h.55Z" />
        </>,
        c,
      )
    case 'whatsapp_business':
    case 'whatsapp':
      return wrap(
        <>
          <path fill="#25D366" d="M12 2.2A9.7 9.7 0 0 0 2.4 11.8c0 1.7.45 3.35 1.3 4.8L2.2 21.8l5.4-1.4a9.7 9.7 0 0 0 4.4 1.05A9.7 9.7 0 1 0 12 2.2Z" />
          <path fill="#fff" d="M17.05 14.55c-.25-.12-1.48-.73-1.7-.81-.23-.09-.4-.12-.57.12-.17.25-.65.81-.8.98-.15.17-.3.19-.55.06-.25-.12-1.05-.39-2-1.23-.74-.66-1.24-1.48-1.39-1.73-.14-.25-.02-.38.11-.5.11-.11.25-.3.37-.45.12-.15.17-.25.25-.42.09-.17.04-.32-.02-.45-.06-.12-.57-1.37-.78-1.88-.2-.48-.41-.42-.57-.43h-.48c-.17 0-.45.06-.68.32-.23.25-.9.88-.9 2.14s.92 2.48 1.05 2.65c.12.17 1.81 2.77 4.39 3.88 1.73.75 2.15.65 2.54.61.39-.04 1.28-.52 1.46-1.03.18-.5.18-.94.12-1.03-.05-.1-.23-.16-.48-.28Z" />
        </>,
        c,
      )
    case 'google_drive':
    case 'drive':
      return wrap(
        <>
          <path fill="#0066DA" d="M4.05 15.75 8.1 8.7l4.05 7.05H4.05Z" />
          <path fill="#00AC47" d="m8.1 8.7 4.05-7.05L16.2 8.7 8.1 8.7Z" />
          <path fill="#FFBA00" d="m12.15 15.75 4.05-7.05 4.05 7.05h-8.1Z" />
          <path fill="#00832D" d="M8.1 8.7h8.1L12.15 1.65 8.1 8.7Z" opacity=".9" />
          <path fill="#2684FC" d="M4.05 15.75h8.1l-4.05 7.05-4.05-7.05Z" opacity=".85" />
        </>,
        c,
      )
    case 'onedrive':
      return wrap(
        <>
          <path fill="#094AB2" d="M9.2 16.8c-2.55 0-4.6-1.9-4.6-4.25 0-1.95 1.35-3.6 3.2-4.15A4.35 4.35 0 0 1 15.8 7.2c.15 0 .3 0 .45.02A3.9 3.9 0 0 1 19.7 11c0 .15 0 .3-.02.45 1.35.5 2.32 1.8 2.32 3.3 0 1.95-1.6 3.55-3.55 3.55H9.2Z" />
          <path fill="#4CC2FF" d="M6.8 15.2c-1.55 0-2.8-1.2-2.8-2.7 0-1.25.85-2.3 2.05-2.65A3.2 3.2 0 0 1 12 8.1c.1 0 .2 0 .3.02A2.85 2.85 0 0 1 15.1 11c0 .1 0 .2-.02.3 1 .35 1.72 1.3 1.72 2.4 0 1.4-1.15 2.55-2.55 2.55H6.8Z" opacity=".95" />
        </>,
        c,
      )
    case 'notion':
      return wrap(
        <>
          <path fill="#000" d="M5.2 3.5h11.3c.5 0 .9.15 1.2.5l1.9 2.1c.25.3.4.65.4 1V19c0 .9-.7 1.5-1.55 1.5H6.35c-.55 0-1-.2-1.3-.55L3.5 17.9c-.3-.35-.45-.75-.45-1.2V5c0-.85.7-1.5 2.15-1.5Z" />
          <path fill="#fff" d="M9.1 7.4h1.55l2.85 7.35h.1V7.4h1.4v9.2h-1.7L10.4 9.15h-.1V16.6H8.9V7.4h.2Z" />
        </>,
        c,
      )
    case 'sharepoint':
      return wrap(
        <>
          <circle cx="9" cy="12" r="5.2" fill="#038387" />
          <circle cx="15.5" cy="9.5" r="4.2" fill="#37C6D0" />
          <circle cx="14.8" cy="15.2" r="3.6" fill="#1A9BA1" />
          <path fill="#fff" d="M7.6 10.2h1.5v1.35H9.9v1.2H9.1V16H7.6v-5.8Z" opacity=".95" />
        </>,
        c,
      )
    case 'coresinistre':
    case 'insurance_core':
      return wrap(
        <>
          <ellipse cx="12" cy="6.5" rx="7" ry="2.8" fill="#1C1917" />
          <path fill="#44403C" d="M5 6.5v4c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8v-4c0 1.55-3.13 2.8-7 2.8S5 8.05 5 6.5Z" />
          <path fill="#292524" d="M5 10.5v4c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8v-4c0 1.55-3.13 2.8-7 2.8s-7-1.25-7-2.8Z" />
          <path fill="#D97757" d="M5 14.5v3c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8v-3c0 1.55-3.13 2.8-7 2.8s-7-1.25-7-2.8Z" />
        </>,
        c,
      )
    case 'erp':
    case 'erp_interne_demo':
      return wrap(
        <>
          <rect x="3" y="4" width="18" height="16" rx="2" fill="#334155" />
          <path fill="#94A3B8" d="M6 8h5v1.4H6V8Zm0 3h12v1.4H6V11Zm0 3h9v1.4H6V14Z" />
          <rect x="14.5" y="7.2" width="4" height="3.2" rx=".6" fill="#D97757" />
        </>,
        c,
      )
    case 'digiclaim':
      return wrap(
        <>
          <rect width="24" height="24" rx="5" fill="#0F766E" />
          <path fill="#fff" d="M7 7h4.2c2.6 0 4.3 1.5 4.3 4s-1.7 4-4.3 4H8.4V17H7V7Zm1.4 1.4v5.2H11c1.75 0 2.85-.95 2.85-2.6S12.75 8.4 11 8.4H8.4Z" />
        </>,
        c,
      )
    case 'micard':
      return wrap(
        <>
          <rect width="24" height="24" rx="5" fill="#0369A1" />
          <rect x="4.5" y="7" width="15" height="10" rx="1.5" fill="#fff" />
          <rect x="6" y="9" width="6" height="1.4" rx=".4" fill="#0369A1" />
          <rect x="6" y="12" width="9" height="1.2" rx=".4" fill="#7DD3FC" />
        </>,
        c,
      )
    case 'pass':
      return wrap(
        <>
          <rect width="24" height="24" rx="5" fill="#B45309" />
          <path fill="#fff" d="M7 7.5h3.2c2.2 0 3.6 1.2 3.6 3.1 0 1.5-.85 2.55-2.2 2.95L14.2 17H12.5l-2.3-3.2H8.4V17H7V7.5Zm1.4 1.35v3.55h1.7c1.25 0 2-.65 2-1.8s-.75-1.75-2-1.75H8.4Z" />
        </>,
        c,
      )
    case 'proassur':
      return wrap(
        <>
          <rect width="24" height="24" rx="5" fill="#6D4C9F" />
          <path fill="#fff" d="M7 7h3.4c2.35 0 3.85 1.25 3.85 3.25S12.75 13.5 10.4 13.5H8.4V17H7V7Zm1.4 1.35v3.8h1.9c1.4 0 2.3-.7 2.3-1.9s-.9-1.9-2.3-1.9H8.4Z" />
        </>,
        c,
      )
    case 'erecours':
      return wrap(
        <>
          <rect width="24" height="24" rx="5" fill="#334155" />
          <path fill="#fff" d="M6.5 12a5.5 5.5 0 1 1 9.4 3.85L17.5 17.5l-1.2 1.2-1.7-1.7A5.5 5.5 0 0 1 6.5 12Zm1.5 0a4 4 0 1 0 8 0 4 4 0 0 0-8 0Z" />
        </>,
        c,
      )
    default:
      return wrap(
        <>
          <rect width="24" height="24" rx="6" fill="#E7E5E4" />
          <circle cx="12" cy="12" r="4" fill="#A8A29E" />
        </>,
        c,
      )
  }
}

function PngMark({ slug, size }) {
  const file = PNG_FILE[slug] || slug
  return (
    <img
      src={`/logos/${file}.png`}
      alt=""
      width={size}
      height={size}
      className="h-full w-full object-contain"
      draggable={false}
    />
  )
}

export function BrandMark({ slug, size = 36, className = '' }) {
  const usePng = PNG_SLUGS.has(slug)
  return (
    <div
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-black/5 ${className}`}
      style={{ width: size, height: size, padding: size > 32 ? 6 : 4 }}
    >
      {usePng ? <PngMark slug={slug} size={size - (size > 32 ? 12 : 8)} /> : <BrandLogo slug={slug} />}
    </div>
  )
}
