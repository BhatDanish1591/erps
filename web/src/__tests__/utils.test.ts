import { describe, it, expect } from 'vitest'
import { capitalize, toTitleCase, truncate, buildQueryString } from '@/utils'

describe('capitalize', () => {
  it('capitalises first letter', () => {
    expect(capitalize('hello')).toBe('Hello')
    expect(capitalize('WORLD')).toBe('World')
  })
})

describe('toTitleCase', () => {
  it('converts snake_case to Title Case', () => {
    expect(toTitleCase('institution_admin')).toBe('Institution Admin')
    expect(toTitleCase('SUPER_ADMIN')).toBe('Super Admin')
  })
})

describe('truncate', () => {
  it('truncates long strings', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...')
    expect(truncate('Short', 10)).toBe('Short')
  })
})

describe('buildQueryString', () => {
  it('builds query string from params', () => {
    expect(buildQueryString({ page: 1, size: 20 })).toBe('?page=1&size=20')
    expect(buildQueryString({ page: 1, name: null })).toBe('?page=1')
    expect(buildQueryString({})).toBe('')
  })
})
