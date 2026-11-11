import { useCallback, useEffect, useState } from 'react'
import { useAuth, useClerk, useUser } from '@clerk/react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { ApiError } from '@/lib/apiClient'
import { BROKERAGE_OPTIONS, type BrokerageId } from '../portfolio/brokerageImport.ts'
import { formatConfiguredAt } from './brokerageConnections.ts'
import {
  deleteBrokerageCredentials,
  deleteLocalAccount,
  downloadAccountExport,
  getSchwabOAuthSetup,
  listBrokerageCredentials,
  startSchwabAuthorize,
  upsertBrokerageCredentials,
  type BrokerageCredentialStatus,
} from './settingsApi.ts'

const DELETE_CONFIRM_TEXT = 'DELETE'

function maskSecret(): string {
  return '••••••••••••••••'
}

function maskAppKey(hint: string): string {
  return `••••••••••••${hint}`
}

function clerkErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object') {
    const errors = (error as { errors?: Array<{ longMessage?: string; message?: string }> }).errors
    const first = errors?.[0]
    if (first?.longMessage) return first.longMessage
    if (first?.message) return first.message
    if (error instanceof Error && error.message) return error.message
  }
  return fallback
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { getToken } = useAuth()
  const { signOut } = useClerk()
  const { isLoaded, user } = useUser()

  const [statuses, setStatuses] = useState<BrokerageCredentialStatus[]>([])
  const [statusesLoading, setStatusesLoading] = useState(true)
  const [schwabCallbackUrl, setSchwabCallbackUrl] = useState('')
  const [schwabAppKey, setSchwabAppKey] = useState('')
  const [schwabAppSecret, setSchwabAppSecret] = useState('')
  const [editingCredentials, setEditingCredentials] = useState(false)
  const [brokerageBusy, setBrokerageBusy] = useState<BrokerageId | null>(null)
  const [brokerageError, setBrokerageError] = useState<string | null>(null)
  const [brokerageNote, setBrokerageNote] = useState<string | null>(null)
  const [copiedCallback, setCopiedCallback] = useState(false)

  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [exportBusy, setExportBusy] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const email = user?.primaryEmailAddress?.emailAddress
  const canDelete = deleteConfirm.trim() === DELETE_CONFIRM_TEXT
  const deleteSelfEnabled = user?.deleteSelfEnabled !== false
  const schwabStatus = statuses.find((row) => row.provider === 'schwab')
  const schwabVaulted = Boolean(schwabStatus)
  const schwabAuthorized = Boolean(schwabStatus?.authorized)
  const showCredentialForm = !schwabVaulted || editingCredentials

  const refreshStatuses = useCallback(async () => {
    const token = await getToken()
    if (!token) {
      setStatuses([])
      return null
    }
    const [rows, setup] = await Promise.all([
      listBrokerageCredentials(token),
      getSchwabOAuthSetup(token),
    ])
    setStatuses(rows)
    setSchwabCallbackUrl(setup.callback_url)
    return rows.find((row) => row.provider === 'schwab') ?? null
  }, [getToken])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setStatusesLoading(true)
      setBrokerageError(null)
      try {
        await refreshStatuses()
      } catch (caught) {
        if (!cancelled) {
          setBrokerageError(
            caught instanceof ApiError
              ? caught.message
              : 'Could not load brokerage credential status.',
          )
        }
      } finally {
        if (!cancelled) setStatusesLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [refreshStatuses])

  useEffect(() => {
    const schwab = searchParams.get('schwab')
    if (schwab !== 'connected') return
    setBrokerageNote('Schwab authorization complete. Access and refresh tokens are vaulted.')
    setBrokerageError(null)
    setEditingCredentials(false)
    void refreshStatuses()
    const next = new URLSearchParams(searchParams)
    next.delete('schwab')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams, refreshStatuses])

  async function pollUntilAuthorized() {
    for (let attempt = 0; attempt < 40; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 1500))
      try {
        const status = await refreshStatuses()
        if (status?.authorized) {
          setBrokerageNote('Schwab authorization complete. Access and refresh tokens are vaulted.')
          setEditingCredentials(false)
          return
        }
      } catch {
        // Keep polling while the other tab finishes OAuth.
      }
    }
  }

  async function copyCallbackUrl() {
    if (!schwabCallbackUrl) return
    try {
      await navigator.clipboard.writeText(schwabCallbackUrl)
      setCopiedCallback(true)
      window.setTimeout(() => setCopiedCallback(false), 2000)
    } catch {
      setBrokerageError('Could not copy the callback URL. Select and copy it manually.')
    }
  }

  async function saveCredentialsOnly() {
    const appKey = schwabAppKey.trim()
    const appSecret = schwabAppSecret.trim()
    if (!appKey || !appSecret) {
      setBrokerageError('Enter both App Key and App Secret to save.')
      setBrokerageNote(null)
      return
    }
    setBrokerageBusy('schwab')
    setBrokerageError(null)
    setBrokerageNote(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in again, then retry.')
      await upsertBrokerageCredentials(token, 'schwab', {
        app_key: appKey,
        app_secret: appSecret,
      })
      setSchwabAppKey('')
      setSchwabAppSecret('')
      setEditingCredentials(false)
      await refreshStatuses()
      setBrokerageNote('App Key and Secret saved to the encrypted vault.')
    } catch (caught) {
      setBrokerageError(
        caught instanceof ApiError
          ? caught.message
          : clerkErrorMessage(caught, 'Could not save Schwab credentials.'),
      )
    } finally {
      setBrokerageBusy(null)
    }
  }

  async function authorizeSchwab() {
    const appKey = schwabAppKey.trim()
    const appSecret = schwabAppSecret.trim()
    if (!schwabVaulted && (!appKey || !appSecret)) {
      setBrokerageError('Enter your Schwab App Key and App Secret, then authorize.')
      setBrokerageNote(null)
      return
    }
    if (editingCredentials && (!appKey || !appSecret)) {
      setBrokerageError('Enter both new App Key and App Secret, or cancel editing.')
      setBrokerageNote(null)
      return
    }

    setBrokerageBusy('schwab')
    setBrokerageError(null)
    setBrokerageNote(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in again, then retry.')
      if (appKey && appSecret) {
        await upsertBrokerageCredentials(token, 'schwab', {
          app_key: appKey,
          app_secret: appSecret,
        })
        setSchwabAppKey('')
        setSchwabAppSecret('')
        setEditingCredentials(false)
        await refreshStatuses()
      }
      const { authorize_url: authorizeUrl } = await startSchwabAuthorize(token)
      const popup = window.open(authorizeUrl, '_blank', 'noopener,noreferrer')
      if (!popup) {
        setBrokerageError('Pop-up blocked. Allow pop-ups for Optify, then try again.')
        return
      }
      setBrokerageNote(
        'Schwab login opened in a new tab. Finish consent there — this page will update when authorization completes.',
      )
      void pollUntilAuthorized()
    } catch (caught) {
      setBrokerageError(
        caught instanceof ApiError
          ? caught.message
          : clerkErrorMessage(caught, 'Could not start Schwab authorization.'),
      )
    } finally {
      setBrokerageBusy(null)
    }
  }

  async function disconnectBrokerage(id: BrokerageId) {
    const option = BROKERAGE_OPTIONS.find((row) => row.id === id)
    setBrokerageBusy(id)
    setBrokerageError(null)
    setBrokerageNote(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in again, then retry.')
      await deleteBrokerageCredentials(token, id)
      await refreshStatuses()
      if (id === 'schwab') {
        setSchwabAppKey('')
        setSchwabAppSecret('')
        setEditingCredentials(false)
      }
      setBrokerageNote(`${option?.label ?? 'Brokerage'} disconnected. Vault entry removed.`)
    } catch (caught) {
      setBrokerageError(
        caught instanceof ApiError
          ? caught.message
          : clerkErrorMessage(caught, `Could not disconnect ${option?.label ?? 'brokerage'}.`),
      )
    } finally {
      setBrokerageBusy(null)
    }
  }

  async function handleDownloadData() {
    setExportBusy(true)
    setExportError(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in again, then retry the download.')
      await downloadAccountExport(token)
    } catch (caught) {
      setExportError(
        caught instanceof ApiError
          ? caught.message
          : caught instanceof Error
            ? caught.message
            : 'Could not download data.',
      )
    } finally {
      setExportBusy(false)
    }
  }

  async function handleDeleteAccount() {
    if (!user || !canDelete) return
    if (!window.confirm('Permanently delete your Optify account and all portfolios?')) return

    setDeleting(true)
    setDeleteError(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in again, then retry account deletion.')
      await deleteLocalAccount(token)
      if (deleteSelfEnabled) {
        await user.delete()
      }
      await signOut()
      navigate('/login', { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError) {
        setDeleteError(caught.message)
      } else {
        setDeleteError(
          clerkErrorMessage(
            caught,
            'Could not delete the account. If Clerk blocked deletion, enable self-serve delete in the Dashboard.',
          ),
        )
      }
    } finally {
      setDeleting(false)
    }
  }

  if (!isLoaded) {
    return <p className="text-sm text-muted-foreground">Loading settings…</p>
  }

  if (!user) {
    return <p className="text-sm text-muted-foreground">Sign in to manage account settings.</p>
  }

  const schwabBusy = brokerageBusy === 'schwab'

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Link brokerages with your own API credentials (BYOK) and manage your account.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Signed in as {email ?? 'your Clerk account'}.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            type="button"
            variant="outline"
            disabled={exportBusy}
            onClick={() => void handleDownloadData()}
          >
            {exportBusy ? 'Downloading…' : 'Download data'}
          </Button>
          {exportError && (
            <Alert variant="destructive">
              <AlertDescription>{exportError}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Brokerages</CardTitle>
          <CardDescription>
            Connect Charles Schwab with your developer App Key and Secret. Secrets stay encrypted
            on the server and are never shown again in full.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {statusesLoading && (
            <p className="text-sm text-muted-foreground">Loading linked brokerages…</p>
          )}

          <div className="space-y-5 rounded-lg border border-border p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-base font-medium">Charles Schwab</p>
                  {schwabAuthorized ? (
                    <Badge variant="secondary">Authorized</Badge>
                  ) : schwabVaulted ? (
                    <Badge variant="outline">Keys saved</Badge>
                  ) : (
                    <Badge variant="outline">Not connected</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {schwabVaulted && schwabStatus
                    ? `${formatConfiguredAt(schwabStatus.updated_at)} · ending in ${schwabStatus.app_key_hint}`
                    : 'Add credentials from your Schwab Developer Portal app (Ready For Use).'}
                </p>
              </div>
              {schwabVaulted && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={schwabBusy}
                  onClick={() => void disconnectBrokerage('schwab')}
                >
                  Disconnect
                </Button>
              )}
            </div>

            {schwabVaulted && !editingCredentials ? (
              <div className="space-y-3 rounded-md bg-muted/40 px-3 py-3">
                <div className="grid gap-1">
                  <p className="text-xs font-medium text-muted-foreground">App Key</p>
                  <p className="font-mono text-sm tracking-wide">
                    {maskAppKey(schwabStatus?.app_key_hint ?? '')}
                  </p>
                </div>
                <div className="grid gap-1">
                  <p className="text-xs font-medium text-muted-foreground">App Secret</p>
                  <p className="font-mono text-sm tracking-wide">{maskSecret()}</p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="px-0"
                  onClick={() => {
                    setEditingCredentials(true)
                    setBrokerageError(null)
                    setBrokerageNote(null)
                  }}
                >
                  Replace credentials
                </Button>
              </div>
            ) : (
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="schwab-app-key">App Key (Client ID)</FieldLabel>
                  <Input
                    id="schwab-app-key"
                    value={schwabAppKey}
                    autoComplete="off"
                    spellCheck={false}
                    placeholder="Paste App Key from Schwab"
                    onChange={(event) => {
                      setSchwabAppKey(event.target.value)
                      setBrokerageError(null)
                      setBrokerageNote(null)
                    }}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="schwab-app-secret">App Secret</FieldLabel>
                  <Input
                    id="schwab-app-secret"
                    type="password"
                    value={schwabAppSecret}
                    autoComplete="new-password"
                    placeholder="Paste App Secret from Schwab"
                    onChange={(event) => {
                      setSchwabAppSecret(event.target.value)
                      setBrokerageError(null)
                      setBrokerageNote(null)
                    }}
                  />
                  <FieldDescription>
                    Shown only while typing. After save, Optify stores an encrypted copy and shows a
                    masked value.
                  </FieldDescription>
                </Field>
                {editingCredentials && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="w-fit px-0"
                    onClick={() => {
                      setEditingCredentials(false)
                      setSchwabAppKey('')
                      setSchwabAppSecret('')
                    }}
                  >
                    Cancel replace
                  </Button>
                )}
              </FieldGroup>
            )}

            <Field>
              <FieldLabel htmlFor="schwab-callback">Callback URL</FieldLabel>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  id="schwab-callback"
                  value={schwabCallbackUrl}
                  readOnly
                  className="font-mono text-xs"
                />
                <Button type="button" variant="outline" onClick={() => void copyCallbackUrl()}>
                  {copiedCallback ? 'Copied' : 'Copy'}
                </Button>
              </div>
              <FieldDescription>
                Register this exact URL in your Schwab developer app.
              </FieldDescription>
            </Field>

            <div className="flex flex-wrap gap-2">
              {showCredentialForm && (
                <Button
                  type="button"
                  variant="outline"
                  disabled={schwabBusy}
                  onClick={() => void saveCredentialsOnly()}
                >
                  {schwabBusy ? 'Saving…' : 'Save keys'}
                </Button>
              )}
              <Button type="button" disabled={schwabBusy} onClick={() => void authorizeSchwab()}>
                {schwabBusy
                  ? 'Opening Schwab…'
                  : schwabAuthorized
                    ? 'Re-authorize in new tab'
                    : 'Authorize in new tab'}
              </Button>
            </div>
          </div>

          {BROKERAGE_OPTIONS.filter((option) => option.id !== 'schwab').map((option) => (
            <div
              key={option.id}
              className="flex flex-col gap-3 rounded-lg border border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{option.label}</p>
                  <Badge variant="outline">Coming soon</Badge>
                </div>
                <p className="text-sm text-muted-foreground">BYOK linking is not available yet.</p>
              </div>
              <Button type="button" disabled>
                Connect
              </Button>
            </div>
          ))}

          {brokerageError && (
            <Alert variant="destructive">
              <AlertDescription>{brokerageError}</AlertDescription>
            </Alert>
          )}
          {brokerageNote && (
            <Alert>
              <AlertDescription>{brokerageNote}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Delete account</CardTitle>
          <CardDescription>
            Permanently remove your Optify data (portfolios, runs, and vaulted brokerage keys) and
            your Clerk sign-in. This cannot be undone.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!deleteSelfEnabled && (
            <Alert>
              <AlertDescription>
                Clerk self-serve deletion is currently disabled. Deleting here still clears Optify
                data; enable “Allow users to delete their accounts” in the Clerk Dashboard to remove
                the sign-in as well.
              </AlertDescription>
            </Alert>
          )}
          <Field>
            <FieldLabel htmlFor="settings-delete-confirm">
              Type {DELETE_CONFIRM_TEXT} to confirm
            </FieldLabel>
            <Input
              id="settings-delete-confirm"
              value={deleteConfirm}
              autoComplete="off"
              placeholder={DELETE_CONFIRM_TEXT}
              onChange={(event) => {
                setDeleteConfirm(event.target.value)
                setDeleteError(null)
              }}
            />
          </Field>
          {deleteError && (
            <Alert variant="destructive">
              <AlertDescription>{deleteError}</AlertDescription>
            </Alert>
          )}
          <Separator />
          <Button
            type="button"
            variant="destructive"
            disabled={deleting || !canDelete}
            onClick={() => void handleDeleteAccount()}
          >
            {deleting ? 'Deleting…' : 'Delete my account'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
