/* Redux Store — v0.58.4
 *
 * Store centralizado com sidebar slice.
 */

import { configureStore } from '@reduxjs/toolkit'
import sidebarReducer from './sidebarSlice'

export const store = configureStore({
  reducer: {
    sidebar: sidebarReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
