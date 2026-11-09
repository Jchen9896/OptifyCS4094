import { SignIn, SignUp } from '@clerk/react'

export default function LoginPage({ signUp = false }: { signUp?: boolean }) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background px-4">
      {signUp ? <SignUp routing="path" path="/sign-up" /> : <SignIn routing="path" path="/login" />}
    </div>
  )
}
