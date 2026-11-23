import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ResourceChart } from '../src/components/ResourceChart';

it('loads bounded history for the selected clock window', async () => {
  const end = Date.UTC(2026, 10, 23, 12);
  const loadHistory = vi.fn(async (minutes: number) => {
    const start = new Date(end - minutes * 60_000).toISOString();
    return {
      start,
      end: new Date(end).toISOString(),
      bucket_seconds: (minutes * 60) / 120,
      items: [
        {
          collected_at: start,
          cpu_percent: 30,
          memory_percent: 40,
          disk_percent: 50,
        },
      ],
    };
  });

  render(<ResourceChart metrics={[]} loadHistory={loadHistory} />);
  await screen.findByText('1 bucket');
  expect(loadHistory).toHaveBeenCalledWith(30);
  fireEvent.click(screen.getByRole('button', { name: '1 h' }));
  await waitFor(() => expect(loadHistory).toHaveBeenCalledWith(60));
  fireEvent.click(screen.getByRole('button', { name: '24 h' }));
  await waitFor(() => expect(loadHistory).toHaveBeenCalledWith(1440));
  expect(screen.getByRole('button', { name: '24 h' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
});
