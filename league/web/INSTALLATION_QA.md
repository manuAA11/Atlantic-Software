# Mobile installation entry

Implemented as a presentation boundary around the existing application. It does not authorize
API access, create users, change member sessions, alter membership rules, or edit routine code.
All member API authentication and gym isolation remain mandatory.

## User experience

- Mobile browser: welcome page with the approved Atlantic icon, universal headline and device-specific instructions.
- Installed app: either `display-mode: standalone` or iOS `navigator.standalone` opens the existing app/login.
- Desktop: ordinary web experience; an optional install button appears when the browser provides a prompt.
- Android/Chromium: a captured `beforeinstallprompt` is shown only after tapping Install; dismissal returns to menu instructions.
- iOS: Share, Add to Home Screen, and Open as App when available. Embedded/alternative browsers get compatible-browser guidance.
- Browser shortcuts that do not launch standalone keep a visible explanation and instructions for adding the app correctly.
- `appinstalled` or accepting the native prompt never unlocks the current mobile browser tab by itself.
- Authentication/recovery/invitation URLs bypass the installation screen for their essential flow; the mobile auth-only state does not show member content afterward.
- Clipboard sharing copies only the site's root URL, never callback tokens or recovery parameters.

The service worker registers outside the content boundary, including while the welcome screen
is displayed. Static caching and explicit update activation are preserved. Updates do not force
a reload on initial service-worker activation or during recognized authentication callbacks.

## Verification scope

| Requested check | Automated evidence | Physical/browser acceptance |
| --- | --- | --- |
| iPhone browser | Device policy and rendered welcome page | Pending |
| Installed iPhone | Both standalone signals and normal app rendering | Pending |
| Android Chrome | Browser gate, conditional prompt, explicit gesture and acceptance | Pending |
| Installed Android | Display-mode signal and normal app rendering | Pending |
| Alternative/embedded browsers | Samsung/Firefox/iOS cases and rendered recovery guidance | Pending |
| Browser/standalone transitions | Media change, pageshow, visibility and older media-listener API | Pending |
| Signed-in sessions | Boundary does not access member storage; existing auth/session implementation preserved | Real installed-session persistence pending |
| PWA updates | Static-only cache test; worker registration moved above gate; callback reload guard | Device update acceptance pending |
| Auth/recovery/invitation links | Path, query, OAuth fragments and hash-route exemptions; auth-only render | Provider end-to-end acceptance pending |

Twenty-seven automated test groups and TypeScript/Vite build pass. Thirteen groups cover the
installation policy, browser-event controller and actual React rendering with simulated platform
signals. These results are not physical iPhone/Android installation evidence. Browser automation
is unavailable in this session; no browser was installed or substituted for that verification.

This installation change is saved in `pruebas`; it has not been published to the live site.
Publishing requires authorization under the requested restriction. Separately, the supported
Site source helper could not reach the hosting Git remote because DNS resolution failed in
the execution environment. That source/publishing connection must work before a supported
publication can complete.
