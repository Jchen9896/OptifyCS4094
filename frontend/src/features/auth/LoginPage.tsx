import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    // Auth API is not implemented yet; continue into the app shell for wireframe flow.
    navigate('/')
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <span className="mb-2 inline-block size-10 rounded-md bg-primary" />
          <CardTitle className="text-2xl">Sign in to Optify</CardTitle>
          <CardDescription>
            Access your portfolios, run historical analysis, and compare allocations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form id="login-form" onSubmit={handleSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="email">Email address</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>
              <Field orientation="horizontal" className="justify-between">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="remember"
                    checked={remember}
                    onCheckedChange={(checked) => setRemember(checked === true)}
                  />
                  <FieldLabel htmlFor="remember" className="font-normal text-muted-foreground">
                    Remember me
                  </FieldLabel>
                </div>
                <span className="text-sm underline-offset-4 hover:underline">Forgot password?</span>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
        <CardFooter className="flex-col gap-4">
          <Button type="submit" form="login-form" className="w-full">
            Sign in
          </Button>
          <FieldDescription className="text-center">
            Don&apos;t have an account?{' '}
            <Link to="/" className="font-medium text-foreground underline-offset-4 hover:underline">
              Sign up
            </Link>
          </FieldDescription>
          <p className="text-center text-xs text-muted-foreground">
            Wireframe flow only — account APIs are not connected yet.
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
