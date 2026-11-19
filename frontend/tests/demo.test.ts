import { describe, expect, it } from 'vitest';
import {
  createDemoIncident,
  createDemoSnapshot,
  updateDemoIncident,
} from '../src/services/demo';

describe('demo incident lifecycle', () => {
  it('preserves resolution time on edits and clears it when reopened', () => {
    const record = createDemoSnapshot().incidents.find(
      (item) => item.status === 'resolved',
    )!;
    const input = {
      title: record.title,
      description: 'Updated notes',
      severity: record.severity,
      status: record.status,
    };
    const edited = updateDemoIncident(record, input);

    expect(edited.resolved_at).toBe(record.resolved_at);
    expect(
      updateDemoIncident(edited, { ...input, status: 'open' }).resolved_at,
    ).toBeNull();
  });

  it('creates open records with generated IDs and no resolution time', () => {
    const input = {
      title: 'Example',
      description: 'Example description',
      severity: 'info' as const,
      occurred_at: new Date().toISOString(),
    };
    const record = createDemoIncident(input);

    expect(record).toMatchObject({
      ...input,
      status: 'open',
      resolved_at: null,
    });
    expect(record.id).toMatch(/^[\da-f-]{36}$/);
  });
});
