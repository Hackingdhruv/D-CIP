import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PageHeader } from './page-header';

describe('PageHeader', () => {
  it('renders the title and description', () => {
    render(<PageHeader title="Cases" description="Investigation workspaces." />);
    expect(screen.getByRole('heading', { name: 'Cases', level: 1 })).toBeInTheDocument();
    expect(screen.getByText('Investigation workspaces.')).toBeInTheDocument();
  });

  it('omits the description when not provided', () => {
    render(<PageHeader title="Audit" />);
    expect(screen.getByRole('heading', { name: 'Audit' })).toBeInTheDocument();
  });
});
