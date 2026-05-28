import { describe, it, expect } from 'vitest'
import { getMigrationStatus, isComponentMigrated, COMPONENT_MIGRATION_MAP } from './index'

describe('Migration Index', () => {
  describe('getMigrationStatus', () => {
    it('returns status for migrated components', () => {
      const buttonStatus = getMigrationStatus('Button')
      expect(buttonStatus).toBeDefined()
      expect(buttonStatus?.status).toBe('completed')
      expect(buttonStatus?.file).toBe('semi-button.tsx')
    })

    it('returns undefined for unknown components', () => {
      const unknownStatus = getMigrationStatus('UnknownComponent')
      expect(unknownStatus).toBeUndefined()
    })
  })

  describe('isComponentMigrated', () => {
    it('returns true for completed components', () => {
      expect(isComponentMigrated('Button')).toBe(true)
      expect(isComponentMigrated('Input')).toBe(true)
      expect(isComponentMigrated('Card')).toBe(true)
      expect(isComponentMigrated('Form')).toBe(true)
      expect(isComponentMigrated('Select')).toBe(true)
      expect(isComponentMigrated('Tabs')).toBe(true)
      expect(isComponentMigrated('Tooltip')).toBe(true)
      expect(isComponentMigrated('Popover')).toBe(true)
      expect(isComponentMigrated('Checkbox')).toBe(true)
      expect(isComponentMigrated('Avatar')).toBe(true)
      expect(isComponentMigrated('Badge')).toBe(true)
      expect(isComponentMigrated('Skeleton')).toBe(true)
    })
  })

  describe('COMPONENT_MIGRATION_MAP', () => {
    it('contains all expected components', () => {
      const expectedComponents = [
        'Button', 'Input', 'Textarea', 'Card', 'Dialog',
        'Form', 'Select', 'Tabs', 'Table', 'Dropdown',
        'Alert', 'Pagination', 'Tooltip', 'Popover',
        'Checkbox', 'Avatar', 'Badge', 'Skeleton'
      ]
      
      expectedComponents.forEach(component => {
        expect(COMPONENT_MIGRATION_MAP[component as keyof typeof COMPONENT_MIGRATION_MAP]).toBeDefined()
      })
    })

    it('has correct status values', () => {
      const completedComponents = [
        'Button', 'Input', 'Textarea', 'Card', 'Dialog',
        'Form', 'Select', 'Tabs', 'Table', 'Dropdown',
        'Alert', 'Pagination', 'Tooltip', 'Popover',
        'Checkbox', 'Avatar', 'Badge', 'Skeleton'
      ]
      
      completedComponents.forEach(component => {
        expect(COMPONENT_MIGRATION_MAP[component as keyof typeof COMPONENT_MIGRATION_MAP].status).toBe('completed')
      })
    })
  })
})

describe('Feature Flags', () => {
  it('USE_SEMI_WRAPPERS is enabled by default', async () => {
    const { FEATURE_FLAGS } = await import('./index')
    expect(FEATURE_FLAGS.USE_SEMI_WRAPPERS).toBe(true)
  })

  it('SEMI_MIGRATION_COMPLETE is true when Phase 1 components are migrated', async () => {
    const { FEATURE_FLAGS } = await import('./index')
    expect(FEATURE_FLAGS.SEMI_MIGRATION_COMPLETE).toBe(true)
  })
})