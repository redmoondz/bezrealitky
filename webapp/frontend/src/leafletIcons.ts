// Leaflet's default marker icon resolves its image URLs relative to its own
// package location, which breaks under Vite's bundling — the standard fix is
// to re-point them at the actual bundled asset URLs. Import once for its
// side effect (e.g. from main.tsx) before any <MapContainer> renders.
import L from 'leaflet'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl })
