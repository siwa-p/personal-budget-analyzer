/**
 * Extracts a human-readable error message from a FastAPI/Pydantic error response.
 *
 * FastAPI returns validation errors as:
 *   { detail: [{ loc, msg, type }, ...] }
 * and simple errors as:
 *   { detail: "some string" }
 */
export function extractApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== 'object') return fallback
  const detail = (data as Record<string, unknown>).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((e) => {
        if (typeof e === 'object' && e !== null && 'msg' in e) {
          const msg = (e as Record<string, string>).msg
          // Pydantic v2 prefixes validation errors with "Value error, " — strip it
          return msg.replace(/^Value error,\s*/i, '')
        }
        return String(e)
      })
      .join('; ')
  }
  return fallback
}
