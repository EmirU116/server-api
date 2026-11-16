import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from '../src/App';

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
});
