import { extractBrowserSubContext, supportsBrowserSubContext } from '~/util/browserSubContext';

describe('extractBrowserSubContext', () => {
  test.each([
    ['Chronio drag fix - ChatGPT', 'ChatGPT', 'Chronio drag fix'],
    ['ChatGPT | ActivityChronio review', 'ChatGPT', 'ActivityChronio review'],
    ['ActivityChronio - Codex', 'Codex', 'ActivityChronio'],
    ['[3] Codex | ActivityChronio', 'Codex', 'ActivityChronio'],
  ])('extracts a two-part service boundary from %s', (title, service, context) => {
    expect(extractBrowserSubContext(service, title)).toBe(context);
  });

  test.each([
    ['ChatGPT', 'ChatGPT'],
    ['New chat - ChatGPT', 'ChatGPT'],
    ['ChatGPT | Log in', 'ChatGPT'],
    ['New session | Codex', 'Codex'],
    ['Review - ActivityChronio - ChatGPT', 'ChatGPT'],
    ['ActivityChronio task', 'Codex'],
  ])('ignores unreliable sub-context from %s', (title, service) => {
    expect(extractBrowserSubContext(service, title)).toBeNull();
  });
});

describe('supportsBrowserSubContext', () => {
  it('limits extraction to the browser tools with known title boundaries', () => {
    expect(supportsBrowserSubContext('ChatGPT')).toBe(true);
    expect(supportsBrowserSubContext('Codex')).toBe(true);
    expect(supportsBrowserSubContext('GitHub')).toBe(false);
  });
});
