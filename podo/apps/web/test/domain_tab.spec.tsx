/**
 * T-067 DomainTabBar 단위 테스트
 * AC-1: 도메인 탭 선택 시 해당 도메인 필터 onChange 호출
 * AC-2: 저신뢰(confidence=low) 시 "직군이 섞여 있어요" 배너 + 전체 탭 기본 활성
 * AC-3: 키보드 좌우 화살표 → 탭 포커스 이동 + aria-selected 업데이트
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import React from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DomainTabBar } from '../components/DomainTabBar'

afterEach(cleanup)

describe('DomainTabBar (T-067)', () => {
  // AC-1: 탭 클릭 → onChange(domain) 호출
  it('test_AC_1_tab_filter_by_domain', () => {
    const onChange = vi.fn()
    render(<DomainTabBar domains={['backend', 'data']} active="all" onChange={onChange} />)

    // "백엔드" 탭 클릭
    fireEvent.click(screen.getByRole('tab', { name: '백엔드' }))
    expect(onChange).toHaveBeenCalledWith('backend')
  })

  // AC-1 추가: 탭 목록에 "전체"가 항상 포함
  it('test_AC_1_includes_all_tab', () => {
    render(<DomainTabBar domains={['backend']} active="all" onChange={vi.fn()} />)
    expect(screen.getByRole('tab', { name: '전체' })).toBeTruthy()
  })

  // AC-1: empty state — active 탭 공고 0건 → empty 메시지 표시 (DomainEmptyState)
  it('test_AC_1_empty_state_no_jobs', () => {
    render(
      <DomainTabBar domains={['backend']} active="backend" onChange={vi.fn()} isEmpty={true} />,
    )
    expect(screen.getByTestId('domain-empty-state')).toBeTruthy()
  })

  // AC-2: 저신뢰(confidence=low) 시 배너 + 전체 탭 기본 활성
  it('test_AC_2_low_confidence_banner', () => {
    render(<DomainTabBar domains={['unknown']} active="all" onChange={vi.fn()} confidence="low" />)
    expect(screen.getByTestId('low-confidence-banner')).toBeTruthy()
    // 전체 탭이 aria-selected=true
    expect(screen.getByRole('tab', { name: '전체' }).getAttribute('aria-selected')).toBe('true')
  })

  // AC-3: 키보드 우측 화살표 → 포커스 이동 + aria-selected 업데이트
  it('test_AC_3_keyboard_navigation_aria', () => {
    const onChange = vi.fn()
    render(<DomainTabBar domains={['backend', 'data']} active="all" onChange={onChange} />)

    const tablist = screen.getByRole('tablist')
    const allTab = screen.getByRole('tab', { name: '전체' })

    // 전체 탭 포커스 후 우측 화살표 → 백엔드 탭으로 포커스 이동
    allTab.focus()
    fireEvent.keyDown(tablist, { key: 'ArrowRight' })

    const backendTab = screen.getByRole('tab', { name: '백엔드' })
    expect(document.activeElement).toBe(backendTab)

    // 좌측 화살표 → 전체 탭으로 복귀
    fireEvent.keyDown(tablist, { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(allTab)
  })

  // AC-3: aria 속성 기본값 검증
  it('test_AC_3_aria_selected_active_tab', () => {
    render(<DomainTabBar domains={['backend', 'data']} active="backend" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: '백엔드' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tab', { name: '전체' }).getAttribute('aria-selected')).toBe('false')
    expect(screen.getByRole('tab', { name: '데이터' }).getAttribute('aria-selected')).toBe('false')
  })
})
