/** Gym and League can share Auth. Leaving League must keep the desktop session. */
export const signOutDevice=(auth:{signOut:(options:{scope:'local'})=>Promise<{error:unknown}>})=>auth.signOut({scope:'local'});
