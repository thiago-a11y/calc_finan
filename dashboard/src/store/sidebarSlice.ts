/* sidebarSlice — v0.58.4
 *
 * Slice Redux para gerenciar estado do sidebar (collapsed/expanded).
 * Persiste em localStorage automaticamente.
 */

import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

interface SidebarState {
  collapsed: boolean  // true = modo mini (só ícones)
  sidebarWidth: number  // largura em px quando expandido
  sidebarWidthCollapsed: number  // largura em px quando colapsado
}

const initialState: SidebarState = {
  collapsed: localStorage.getItem('sidebar_collapsed') === 'true',
  sidebarWidth: 240,
  sidebarWidthCollapsed: 64,
}

const sidebarSlice = createSlice({
  name: 'sidebar',
  initialState,
  reducers: {
    toggleSidebar(state) {
      state.collapsed = !state.collapsed
      localStorage.setItem('sidebar_collapsed', String(state.collapsed))
    },
    setCollapsed(state, action: PayloadAction<boolean>) {
      state.collapsed = action.payload
      localStorage.setItem('sidebar_collapsed', String(state.collapsed))
    },
  },
})

export const { toggleSidebar, setCollapsed } = sidebarSlice.actions
export default sidebarSlice.reducer
