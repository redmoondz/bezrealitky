import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/browse', icon: '📋', label: 'Browse' },
  { to: '/liked', icon: '❤️', label: 'Liked' },
  { to: '/search', icon: '🔍', label: 'Search' },
  { to: '/charts', icon: '📊', label: 'Charts' },
  { to: '/help', icon: 'ℹ️', label: 'Help' },
]

const ADMIN_TAB = { to: '/admin', icon: '🛠', label: 'Admin' }

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
          <span className="tab-bar__icon">{tab.icon}</span>
          <span className="tab-bar__label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
