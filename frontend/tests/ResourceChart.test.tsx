import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ResourceChart } from '../src/components/ResourceChart';
import type { MetricHistory } from '../src/types';

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

const start = Date.UTC(2026, 10, 23, 12);
const empty = {
  start: new Date(start).toISOString(),
  end: new Date(start + 30 * 60_000).toISOString(),
  bucket_seconds: 15,
  items: [],
};

it('draws two groups of lines and CPU fill around a missing bucket', async () => {
  const loadHistory = async () => ({
    ...empty,
    items: [0, 15, 45, 60].map((seconds) => ({
      collected_at: new Date(start + seconds * 1000).toISOString(),
      cpu_percent: 30,
      memory_percent: 40,
      disk_percent: 50,
    })),
  });

  render(<ResourceChart metrics={[]} loadHistory={loadHistory} />);
  const chart = await screen.findByRole('img');
  const lines = [...chart.querySelectorAll('polyline')];
  expect(lines).toHaveLength(6);
  for (const line of lines) {
    expect(line.getAttribute('points')?.split(' ')).toHaveLength(2);
  }
  const fills = [...chart.querySelectorAll('path')];
  expect(fills).toHaveLength(2);
  const firstEnd = fills[0].getAttribute('d')?.match(/L([\d.]+),205 Z$/)?.[1];
  const secondStart = fills[1].getAttribute('d')?.match(/^M([\d.]+),205 /)?.[1];
  expect(Number(firstEnd)).toBeCloseTo(53.67);
  expect(Number(secondStart)).toBeCloseTo(65);
});

it('shows loading until a successful empty response arrives', async () => {
  let resolve!: (value: typeof empty) => void;
  const loadHistory = () =>
    new Promise<typeof empty>((done) => {
      resolve = done;
    });
  render(<ResourceChart metrics={[]} loadHistory={loadHistory} />);

  expect(screen.getByRole('status')).toHaveTextContent(
    'Loading metric history',
  );
  expect(screen.queryByText(/No measurements/)).not.toBeInTheDocument();
  resolve(empty);
  expect(await screen.findByText(/No measurements/)).toBeInTheDocument();
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('shows the failure without presenting it as empty history', async () => {
  const loadHistory = async () => {
    throw new Error('History request failed');
  };
  render(<ResourceChart metrics={[]} loadHistory={loadHistory} />);

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'History request failed',
  );
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(screen.queryByText(/No measurements/)).not.toBeInTheDocument();
});

it('keeps the chart during a delayed refresh and shows the failure alongside it', async () => {
  vi.useFakeTimers();
  try {
    const history: MetricHistory = {
      ...empty,
      items: [
        {
          collected_at: empty.start,
          cpu_percent: 30,
          memory_percent: 40,
          disk_percent: 50,
        },
      ],
    };
    let rejectRefresh!: (error: Error) => void;
    const loadHistory = vi
      .fn(async () => history)
      .mockImplementationOnce(async () => history)
      .mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectRefresh = reject;
          }),
      );
    await act(async () => {
      render(<ResourceChart metrics={[]} loadHistory={loadHistory} />);
    });
    const chart = screen.getByRole('img');

    await act(() => vi.advanceTimersByTimeAsync(30_000));
    expect(loadHistory).toHaveBeenCalledTimes(2);
    expect(chart).toBeVisible();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();

    await act(async () => rejectRefresh(new Error('Network unavailable')));
    expect(screen.getByRole('alert')).toHaveTextContent('Network unavailable');
    expect(chart).toBeVisible();
    expect(screen.getByText('1 bucket')).toBeVisible();

    await act(() => vi.advanceTimersByTimeAsync(30_000));
    expect(loadHistory).toHaveBeenCalledTimes(3);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(chart).toBeVisible();
  } finally {
    vi.useRealTimers();
  }
});
