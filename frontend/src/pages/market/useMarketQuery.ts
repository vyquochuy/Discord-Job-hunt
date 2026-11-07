import { useEffect, useState } from 'react';

// No cache: changing the runtime API base must never reuse another server's data.
export function useMarketQuery<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ key: string; data?: T; error?: string }>({ key: '' });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ key });
    load(controller.signal).then(data => {
      if (active) setState({ key, data });
    }).catch(error => {
      if (active && !controller.signal.aborted) setState({ key, error: error instanceof Error ? error.message : 'Không thể tải dữ liệu.' });
    });
    return () => { active = false; controller.abort(); };
    // The serialized key describes every request input; inline loaders are intentional.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state.key === key ? state : { key };
}
