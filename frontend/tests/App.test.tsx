import {
  fireEvent,
  act,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { createDemoSnapshot } from '../src/services/demo';

describe('demo workspace', () => {
  it('labels sample data and makes no network calls on startup', () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    render(<App />);

    expect(
      screen.getByRole('heading', { name: 'Server overview' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'You’re viewing sample data. No live server is connected.',
      ),
    ).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('navigates to metrics and paginates measurements', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Metrics' }));

    expect(
      screen.getByRole('heading', { name: 'Measurement history' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Showing 1–10 of 96')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText('Showing 11–20 of 96')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
  });

  it('filters and searches incident records', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /^Incidents/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Resolved' }));

    expect(
      screen.getByRole('button', { name: 'Database connection restored' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Elevated CPU utilization' }),
    ).not.toBeInTheDocument();
    fireEvent.change(
      screen.getByRole('textbox', { name: 'Search incidents' }),
      { target: { value: 'nonexistent' } },
    );
    expect(screen.getByText('No matching incidents')).toBeInTheDocument();
  });

  it('creates, updates, resolves, and deletes an incident with confirmation', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'New incident' }));
    let dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Title'), {
      target: { value: 'Test server error' },
    });
    fireEvent.change(within(dialog).getByLabelText('Description'), {
      target: { value: 'A controlled error for the demo workflow.' },
    });
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Create incident' }),
    );

    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Test server error' }));
    dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Status'), {
      target: { value: 'resolved' },
    });
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Save changes' }),
    );
    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Test server error' }));
    dialog = screen.getByRole('dialog');
    expect(within(dialog).getByLabelText('Status')).toHaveValue('resolved');
    expect(
      within(dialog).getByText('Resolved', { selector: 'dt' }),
    ).toBeInTheDocument();
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Delete incident' }),
    );
    expect(
      within(dialog).getByText(
        'Delete this incident permanently? This cannot be undone.',
      ),
    ).toBeInTheDocument();
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Keep incident' }),
    );
    expect(
      screen.queryByRole('button', { name: 'Confirm deletion' }),
    ).not.toBeInTheDocument();
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Delete incident' }),
    );
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Confirm deletion' }),
    );

    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    expect(
      screen.queryByRole('button', { name: 'Test server error' }),
    ).not.toBeInTheDocument();
  });

  it('rejects whitespace-only incident input', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'New incident' }));
    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: '   ' },
    });
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: '   ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Create incident' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'A title and description are required.',
    );
  });

  it('keeps API failures separate from demo data and can return to demo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{}', { status: 401 })),
    );
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Connect API' }));
    fireEvent.change(screen.getByLabelText('Bearer token'), {
      target: { value: 'dummy-test-token' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Your session is not authorized.',
      ),
    );
    expect(screen.queryByText('27.5')).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        'You’re viewing sample data. No live server is connected.',
      ),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New incident' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Explore demo data' }));
    expect(
      screen.getByText(
        'You’re viewing sample data. No live server is connected.',
      ),
    ).toBeInTheDocument();
  });

  it('displays live health and identity without claiming incidents are empty', async () => {
    const demo = createDemoSnapshot();
    const fetch = vi.fn().mockImplementation(async (path: string) => {
      if (path.endsWith('/server'))
        return Response.json({ ...demo.server, hostname: 'real-local-host' });
      if (path.includes('/health?')) return Response.json(demo.health);
      if (path.endsWith('/metrics?limit=100'))
        return Response.json({ items: [], total: 0, limit: 100, offset: 0 });
      throw new Error('Unexpected route');
    });
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Connect API' }));
    fireEvent.change(screen.getByLabelText('Bearer token'), {
      target: { value: 'dummy-test-token' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }));

    expect(await screen.findByText('real-local-host')).toBeInTheDocument();
    expect(screen.getByText('All systems operational')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Incidents unavailable' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New incident' })).toBeDisabled();
    expect(
      screen.queryByText('No open issues in loaded records'),
    ).not.toBeInTheDocument();
    expect(fetch.mock.calls.some(([path]) => path.includes('/incidents'))).toBe(
      false,
    );
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    fireEvent.click(screen.getByRole('button', { name: 'Metrics' }));
    expect(
      screen.getByText('No measurements recorded yet.'),
    ).toBeInTheDocument();
    expect(screen.queryByText('27.5')).not.toBeInTheDocument();
  });

  it('renders stored API metrics and refreshes them without calling incidents', async () => {
    const demo = createDemoSnapshot();
    let cpu = 12.3;
    const fetch = vi.fn().mockImplementation(async (path: string) => {
      if (path.endsWith('/server')) return Response.json(demo.server);
      if (path.includes('/health?')) return Response.json(demo.health);
      if (path.endsWith('/metrics?limit=100')) {
        return Response.json({
          items: [{ ...demo.metrics[0], cpu_percent: cpu }],
          total: 1,
          limit: 100,
          offset: 0,
        });
      }
      throw new Error('Unexpected route');
    });
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Connect API' }));
    fireEvent.change(screen.getByLabelText('Bearer token'), {
      target: { value: 'dummy-test-token' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }));

    expect(await screen.findByText('12.3')).toBeInTheDocument();
    cpu = 19.8;
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    expect(await screen.findByText('19.8')).toBeInTheDocument();
    expect(screen.queryByText('12.3')).not.toBeInTheDocument();
    expect(fetch.mock.calls.some(([path]) => path.includes('/incidents'))).toBe(
      false,
    );
  });

  it('polls live measurements every five seconds and stops when unmounted', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const demo = createDemoSnapshot();
    let cpu = 12.3;
    const fetch = vi.fn().mockImplementation(async (path: string) => {
      if (path.endsWith('/server')) return Response.json(demo.server);
      if (path.includes('/health?')) return Response.json(demo.health);
      return Response.json({
        items: [{ ...demo.metrics[0], cpu_percent: cpu }],
        total: 1,
        limit: 100,
        offset: 0,
      });
    });
    vi.stubGlobal('fetch', fetch);
    const { unmount } = render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Connect API' }));
    fireEvent.change(screen.getByLabelText('Bearer token'), {
      target: { value: 'dummy-reader' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }));
    expect(await screen.findByText('12.3')).toBeInTheDocument();
    cpu = 22.4;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(screen.getByText('22.4')).toBeInTheDocument();
    expect(
      screen.queryByText('Checking in with your server…'),
    ).not.toBeInTheDocument();
    const calls = fetch.mock.calls.length;
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(fetch).toHaveBeenCalledTimes(calls);
  });

  it('shows polling failure and recovers on a later poll without overlapping requests', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const demo = createDemoSnapshot();
    let metricCalls = 0;
    let finishPending: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (path: string) => {
        if (path.endsWith('/server')) return Response.json(demo.server);
        if (path.includes('/health?')) return Response.json(demo.health);
        metricCalls += 1;
        if (metricCalls === 2) {
          return new Promise<Response>((resolve) => {
            finishPending = resolve;
          });
        }
        return Response.json({
          items: [{ ...demo.metrics[0], cpu_percent: 12.3 }],
          total: 1,
          limit: 100,
          offset: 0,
        });
      }),
    );
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Connect API' }));
    fireEvent.change(screen.getByLabelText('Bearer token'), {
      target: { value: 'dummy-reader' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }));
    expect(await screen.findByText('12.3')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(metricCalls).toBe(2);
    await act(async () => {
      finishPending!(new Response('{}', { status: 503 }));
    });
    expect(screen.getByRole('alert')).toHaveTextContent(
      'temporarily unavailable',
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('12.3')).toBeInTheDocument();
  });
});
