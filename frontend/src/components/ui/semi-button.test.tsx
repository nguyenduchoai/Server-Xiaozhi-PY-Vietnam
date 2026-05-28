import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './semi-button'

vi.mock('@douyinfe/semi-ui', () => ({
  Button: vi.fn(({ children, disabled, loading, className, ...props }) => (
    <button
      data-testid="semi-button"
      className={className}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? 'Loading...' : children}
    </button>
  )),
}))

describe('SemiButton Component', () => {
  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<Button>Click me</Button>)
      expect(screen.getByText('Click me')).toBeDefined()
    })

    it('renders button element', () => {
      render(<Button>Test Button</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDefined()
    })
  })

  describe('Variants', () => {
    it('renders primary variant', () => {
      render(<Button variant="primary">Primary</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDefined()
      expect(button.className).toContain('bg-blue-500')
    })

    it('renders secondary variant', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('bg-secondary')
    })

    it('renders ghost variant', () => {
      render(<Button variant="ghost">Ghost</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('hover:bg-accent')
    })

    it('renders danger variant', () => {
      render(<Button variant="danger">Danger</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('bg-destructive')
    })

    it('renders link variant', () => {
      render(<Button variant="link">Link</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('underline-offset-4')
    })
  })

  describe('Sizes', () => {
    it('renders default size', () => {
      render(<Button size="default">Default</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('h-9')
    })

    it('renders small size', () => {
      render(<Button size="small">Small</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('h-8')
    })

    it('renders large size', () => {
      render(<Button size="large">Large</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('h-10')
    })

    it('renders icon size as round', () => {
      render(<Button size="icon">Icon</Button>)
      const button = screen.getByRole('button')
      expect(button.className).toContain('rounded-full')
    })
  })

  describe('States', () => {
    it('renders disabled state', () => {
      render(<Button disabled>Disabled</Button>)
      const button = screen.getByRole('button') as HTMLButtonElement
      expect(button.disabled).toBe(true)
      expect(button.className).toContain('disabled:opacity-50')
    })

    it('renders loading state', () => {
      render(<Button loading>Loading</Button>)
      expect(screen.getByText('Loading...')).toBeDefined()
    })
  })

  describe('Accessibility', () => {
    it('can receive focus', () => {
      render(<Button>Focusable</Button>)
      const button = screen.getByRole('button')
      button.focus()
      expect(document.activeElement).toBe(button)
    })
  })
})