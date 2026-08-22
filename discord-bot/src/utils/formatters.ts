/**
 * Format a job URL to show the website domain and path clearly before opening.
 * Example: `[topcv.vn/viec-lam/backend...](https://www.topcv.vn/viec-lam/backend/123)`
 */
export function formatJobLink(url?: string | null, source?: string | null): string {
  if (!url || !url.trim()) {
    return '*(Chưa có link)*';
  }
  const cleanUrl = url.trim();
  try {
    const parsed = new URL(cleanUrl);
    const domain = parsed.hostname.replace(/^www\./, '');
    const path = parsed.pathname;
    let pathSnippet = path;
    if (pathSnippet.length > 35) {
      pathSnippet = pathSnippet.substring(0, 32) + '...';
    }
    const label = `${domain}${pathSnippet}`;
    return `[${label}](${cleanUrl})`;
  } catch {
    const label = cleanUrl.replace(/^https?:\/\/(www\.)?/, '');
    const shortLabel = label.length > 35 ? label.substring(0, 32) + '...' : label;
    return `[${shortLabel}](${cleanUrl})`;
  }
}
