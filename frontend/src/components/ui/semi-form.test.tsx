/**
 * Unit Tests for Semi Form Components
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Form, FormInput, FormSelect } from './semi-form'

vi.mock('@douyinfe/semi-ui', () => {
  const Input = vi.fn(({ placeholder, ...props }: any) => (
    <input data-testid="semi-input" placeholder={placeholder} {...props} />
  ))
  const TextArea = vi.fn(({ placeholder, ...props }: any) => (
    <textarea data-testid="semi-textarea" placeholder={placeholder} {...props} />
  ))
  const Select = vi.fn(({ placeholder, options, ...props }: any) => (
    <select data-testid="semi-select" {...props}>
      <option value="">{placeholder || 'Select...'}</option>
      {options?.map((opt: { value: string; label: string }) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  ))
  
  const FormField = vi.fn(({ children, label, name, ...props }: any) => (
    <div data-testid="form-field" data-name={name} {...props}>
      {label && <label data-testid="form-label">{label}</label>}
      {children}
    </div>
  ))
  
  const FormComponent: any = vi.fn().mockImplementation(({ children, ...props }: any) => (
    <form data-testid="semi-form" {...props}>{children}</form>
  ))
  
  FormComponent.Field = FormField
  FormComponent.Select = Select
  
  return {
    Form: FormComponent,
    Input,
    TextArea,
    Select,
  }
})

describe('Semi Form Components', () => {
  describe('Form', () => {
    it('renders without crashing', () => {
      render(<Form>Test Form</Form>)
      expect(screen.getByText('Test Form')).toBeDefined()
    })

    it('handles submit callback', () => {
      const handleSubmit = vi.fn()
      render(<Form onSubmit={handleSubmit}>Test</Form>)
      expect(handleSubmit).not.toHaveBeenCalled()
    })

    it('accepts disabled prop', () => {
      render(<Form disabled>Test</Form>)
      expect(screen.getByText('Test')).toBeDefined()
    })
  })

  describe('FormInput', () => {
    it('renders input field', () => {
      render(<FormInput field="email" label="Email" placeholder="Enter email" />)
      expect(screen.getByTestId('semi-input')).toBeDefined()
    })

    it('displays label', () => {
      render(<FormInput field="name" label="Name" />)
      expect(screen.getByTestId('form-label')).toBeDefined()
    })

    it('handles placeholder text', () => {
      render(<FormInput field="test" placeholder="Test placeholder" />)
      expect(screen.getByPlaceholderText('Test placeholder')).toBeDefined()
    })
  })

  describe('FormSelect', () => {
    it('renders select dropdown', () => {
      render(
        <FormSelect
          field="country"
          label="Country"
          placeholder="Select country"
          options={[
            { label: 'Vietnam', value: 'vn' },
            { label: 'USA', value: 'us' },
          ]}
        />
      )
      expect(screen.getByTestId('semi-select')).toBeDefined()
    })

    it('displays options', () => {
      render(
        <FormSelect
          field="status"
          options={[
            { label: 'Active', value: 'active' },
            { label: 'Inactive', value: 'inactive' },
          ]}
        />
      )
      expect(screen.getByText('Active')).toBeDefined()
      expect(screen.getByText('Inactive')).toBeDefined()
    })
  })
})