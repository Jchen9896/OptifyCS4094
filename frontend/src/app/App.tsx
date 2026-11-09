import { BrowserRouter } from 'react-router-dom'
import { ClerkProvider } from '@clerk/react'
import { AppRoutes } from './routes.tsx'

export default function App() {
  const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
  if (!publishableKey) return <p>Set VITE_CLERK_PUBLISHABLE_KEY to start Optify.</p>
  return (
    <ClerkProvider publishableKey={publishableKey} signInUrl="/login" signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/" signUpFallbackRedirectUrl="/">
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ClerkProvider>
  )
}
