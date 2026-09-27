import { z } from '@vben/common-ui';

import { socialAuthRedirectApi } from '#/api/core/auth';

import { readRedirect } from '../../../router/session-access';

const contextSchema = z.object({
  type: z.number().int().positive(),
  codeParameter: z.string().regex(/^[a-zA-Z][a-zA-Z0-9_]*$/),
  tenantId: z
    .string()
    .regex(/^[1-9]\d{0,18}$/)
    .optional(),
  returnPath: z.string(),
  bindingAccountId: z.string().min(1).optional(),
});
export type SocialOAuthContext = z.infer<typeof contextSchema>;
const contextKey = 'dushan:social-oauth:';

export function socialCallbackUri() {
  return new URL(
    `${import.meta.env.BASE_URL}auth/social-login`,
    location.origin,
  ).href;
}

export async function beginSocialOAuth(context: SocialOAuthContext) {
  const value = contextSchema.parse(context);
  value.returnPath = readRedirect(value.returnPath, '');
  const url = new URL(
    await socialAuthRedirectApi(
      value.type,
      socialCallbackUri(),
      value.tenantId,
    ),
  );
  const state = url.searchParams.get('state');
  if (
    url.protocol !== 'https:' ||
    url.username ||
    url.password ||
    !state ||
    url.searchParams.getAll('state').length !== 1
  ) {
    throw new Error('Invalid OAuth authorization URL');
  }
  sessionStorage.setItem(`${contextKey}${state}`, JSON.stringify(value));
  window.location.assign(url.href);
}

export function consumeSocialContext(state: string): SocialOAuthContext {
  const key = `${contextKey}${state}`;
  const value = sessionStorage.getItem(key);
  sessionStorage.removeItem(key);
  const context = contextSchema.parse(
    value === null ? null : JSON.parse(value),
  );
  context.returnPath = readRedirect(context.returnPath, '');
  return context;
}

export function socialCallbackCode(
  codeParameter: string,
  query: Record<string, unknown>,
): string {
  const code = query[codeParameter];
  return z.string().min(1).parse(code);
}
