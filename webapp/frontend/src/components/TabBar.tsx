import { NavLink } from 'react-router-dom'

import adminIcon from '../assets/icons/admin.png'
import browseIcon from '../assets/icons/browse.png'
import chartsIcon from '../assets/icons/charts.png'
import helpIcon from '../assets/icons/help.png'
import likedIcon from '../assets/icons/liked.png'
import searchIcon from '../assets/icons/search.png'

const TABS = [
  { to: '/browse', icon: browseIcon, label: 'Browse' },
  { to: '/liked', icon: likedIcon, label: 'Liked' },
  { to: '/search', icon: searchIcon, label: 'Search' },
  { to: '/charts', icon: chartsIcon, label: 'Charts' },
  { to: '/help', icon: helpIcon, label: 'Help' },
]

const ADMIN_TAB = { to: '/admin', icon: adminIcon, label: 'Admin' }

export default function TabBar({ isAdmin = false }: { isAdmin?: boolean }) {
  const tabs = isAdmin ? [...TABS, ADMIN_TAB] : TABS
  return (
    <nav className="tab-bar">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) => `tab-bar__item${isActive ? ' tab-bar__item--active' : ''}`}
        >
          {/* Icons are white silhouette PNGs — masked with currentColor so they
              pick up the same inactive/active tint as the label. */}
          <span
            className="tab-bar__icon"
            style={{ WebkitMaskImage: `url(${tab.icon})`, maskImage: `url(${tab.icon})` }}
          />
          <span className="tab-bar__label">{tab.label}</span>
          <span className="tab-bar__indicator" />
        </NavLink>
      ))}
    </nav>
  )
}
