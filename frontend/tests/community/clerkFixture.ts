const getToken = async () => null
export const useAuth = () => ({ isLoaded: true, isSignedIn: false, userId: null, getToken })
export const useUser = () => ({ user: { firstName: 'Fixture', primaryEmailAddress: { emailAddress: 'fixture@example.test' } } })
export const useClerk = () => ({ signOut: () => { window.alert('Fixture only. No real Clerk session was changed.') } })
