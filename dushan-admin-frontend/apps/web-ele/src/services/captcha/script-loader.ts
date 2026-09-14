interface ScriptEntry {
  identity: string;
  loaded: boolean;
  references: number;
  script: HTMLScriptElement | undefined;
  ready: Promise<void>;
  cancel: () => void;
}
const scripts = new Map<string, ScriptEntry>();

export function acquireCaptchaScript(
  url: string,
  signal: AbortSignal,
  identity: string,
  prepare?: () => void,
) {
  signal.throwIfAborted();
  let entry = scripts.get(url);
  if (entry && entry.identity !== identity)
    throw new Error('同一页面不能混用不同的验证码 SDK 配置');
  if (!entry) {
    prepare?.();
    const script = document.createElement('script');
    script.src = url;
    script.async = true;
    const listeners = new AbortController();
    let timeout: ReturnType<typeof setTimeout>;
    const deferred = Promise.withResolvers<undefined>();
    const ready = deferred.promise;
    const created: ScriptEntry = {
      identity,
      loaded: false,
      references: 0,
      script,
      ready,
      cancel: () => {
        clearTimeout(timeout);
        listeners.abort();
        script.remove();
        deferred.reject(new DOMException('验证码脚本加载已取消', 'AbortError'));
      },
    };
    const fail = () => {
      clearTimeout(timeout);
      listeners.abort();
      script.remove();
      if (scripts.get(url) === created) scripts.delete(url);
      deferred.reject(new Error('验证码脚本加载失败'));
    };
    script.addEventListener(
      'load',
      () => {
        clearTimeout(timeout);
        listeners.abort();
        created.loaded = true;
        deferred.resolve(undefined);
      },
      { signal: listeners.signal },
    );
    script.addEventListener('error', fail, { signal: listeners.signal });
    timeout = setTimeout(fail, 10_000);
    scripts.set(url, created);
    entry = created;
    document.head.append(script);
  }
  const shared = entry;
  shared.references += 1;
  const waiter = Promise.withResolvers<undefined>();
  let released = false;
  const release = () => {
    if (released) return;
    released = true;
    signal.removeEventListener('abort', onAbort);
    waiter.reject(new DOMException('验证码脚本等待已取消', 'AbortError'));
    shared.references -= 1;
    if (shared.references === 0) {
      shared.script?.remove();
      shared.script = undefined;
      if (!shared.loaded) {
        shared.cancel();
        if (scripts.get(url) === shared) scripts.delete(url);
      }
    }
  };
  const onAbort = () => release();
  shared.ready.then(
    () => {
      if (!released) waiter.resolve(undefined);
    },
    (error) => {
      waiter.reject(error);
      release();
    },
  );
  const ready = waiter.promise;
  signal.addEventListener('abort', onAbort, { once: true });
  return { ready, release };
}
