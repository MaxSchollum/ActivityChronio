const SERVICE_NAMES = new Set(['ChatGPT', 'Codex']);

const GENERIC_CONTEXT_PATTERN =
  /^(?:chatgpt|codex|openai|home|loading|log ?in|login|sign (?:in|up)|auth(?:entication)?|new(?: chat| conversation| session| task)?|untitled(?: chat| conversation| session| task)?)$/i;

function normalizeTitlePart(value: string): string {
  return (value || '')
    .replace(/^\s*(?:\(\d+\)|\[\d+\]|\d+)\s+/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function isServiceName(service: string, value: string): boolean {
  return value.toLowerCase() === service.toLowerCase();
}

export function supportsBrowserSubContext(service: string): boolean {
  return SERVICE_NAMES.has(service);
}

export function extractBrowserSubContext(service: string, title: string): string | null {
  if (!supportsBrowserSubContext(service)) return null;

  const titleParts = normalizeTitlePart(title)
    .split(/\s+(?:-|\|)\s+/)
    .map(normalizeTitlePart)
    .filter(Boolean);

  if (titleParts.length !== 2) return null;

  let context = '';
  if (isServiceName(service, titleParts[0])) {
    context = titleParts[1];
  } else if (isServiceName(service, titleParts[1])) {
    context = titleParts[0];
  }

  if (!context || GENERIC_CONTEXT_PATTERN.test(context)) return null;
  return context;
}
