// icons.jsx — Tabler-style outline icons as React components.
// All icons render at currentColor and accept size + strokeWidth.

const TablerIcon = ({ size = 16, sw = 1.5, children, style, className }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={sw}
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{ flexShrink: 0, display: "inline-block", verticalAlign: "middle", ...style }}
    className={className}
  >
    {children}
  </svg>
);

const Icons = {
  Bolt: (p) => <TablerIcon {...p}><path d="M13 3 4 14h7l-1 7 9-11h-7l1-7Z" /></TablerIcon>,
  Search: (p) => <TablerIcon {...p}><circle cx="10" cy="10" r="6" /><path d="m20 20-4.35-4.35" /></TablerIcon>,
  Plus: (p) => <TablerIcon {...p}><path d="M12 5v14M5 12h14" /></TablerIcon>,
  X: (p) => <TablerIcon {...p}><path d="M18 6 6 18M6 6l12 12" /></TablerIcon>,
  Check: (p) => <TablerIcon {...p}><path d="m5 12 5 5L20 7" /></TablerIcon>,
  ChevronLeft: (p) => <TablerIcon {...p}><path d="m15 6-6 6 6 6" /></TablerIcon>,
  ChevronRight: (p) => <TablerIcon {...p}><path d="m9 6 6 6-6 6" /></TablerIcon>,
  ChevronDown: (p) => <TablerIcon {...p}><path d="m6 9 6 6 6-6" /></TablerIcon>,
  ArrowLeft: (p) => <TablerIcon {...p}><path d="M5 12h14M5 12l6-6M5 12l6 6" /></TablerIcon>,
  ArrowRight: (p) => <TablerIcon {...p}><path d="M5 12h14M13 6l6 6-6 6" /></TablerIcon>,
  Eye: (p) => <TablerIcon {...p}><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></TablerIcon>,
  EyeOff: (p) => <TablerIcon {...p}><path d="M10.58 5.08A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a16.7 16.7 0 0 1-2.36 3.16M6.61 6.61A16.6 16.6 0 0 0 2 12s3.5 7 10 7a10.7 10.7 0 0 0 5.39-1.4" /><path d="m3 3 18 18" /><path d="M9.88 9.88a3 3 0 0 0 4.24 4.24" /></TablerIcon>,
  User: (p) => <TablerIcon {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></TablerIcon>,
  Users: (p) => <TablerIcon {...p}><circle cx="9" cy="8" r="3.5" /><path d="M2 20a7 7 0 0 1 14 0" /><circle cx="17" cy="8" r="3" /><path d="M16.5 14a5 5 0 0 1 5.5 5" /></TablerIcon>,
  Message: (p) => <TablerIcon {...p}><path d="M4 5h16v11H8l-4 4Z" /></TablerIcon>,
  MessageDots: (p) => <TablerIcon {...p}><path d="M4 5h16v11H8l-4 4Z" /><circle cx="9" cy="10.5" r=".5" fill="currentColor" /><circle cx="12" cy="10.5" r=".5" fill="currentColor" /><circle cx="15" cy="10.5" r=".5" fill="currentColor" /></TablerIcon>,
  Send: (p) => <TablerIcon {...p}><path d="m4 12 17-8-4 18-5-7-8-3Z" /><path d="M12 15 21 4" /></TablerIcon>,
  Library: (p) => <TablerIcon {...p}><path d="M4 4h4v16H4zM10 4h4v16h-4zM16 6l3-1 3 14-3 1-3-14Z" /></TablerIcon>,
  Settings: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="3" /><path d="m19.4 15-1.6 1 .5 2-1.8 1-1.5-1.5L13 18l-1 2h-2l-1-2-2 .5-1.8-1 .5-2L4 14l1.6-1L4 11l1.6-1-.5-2L7 7l2 .5L10 6l1-2h2l1 2 2-.5L17.8 7l-.5 2L19 11l-1.6 1L19 13Z" /></TablerIcon>,
  Logout: (p) => <TablerIcon {...p}><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M10 12H3M3 12l4-4M3 12l4 4" /></TablerIcon>,
  Filter: (p) => <TablerIcon {...p}><path d="M4 5h16l-6 8v6l-4-2v-4Z" /></TablerIcon>,
  Tag: (p) => <TablerIcon {...p}><path d="m11 4 9 9-7 7-9-9V4Z" /><circle cx="8" cy="8" r="1.4" /></TablerIcon>,
  Flame: (p) => <TablerIcon {...p}><path d="M12 21c-3.3 0-6-2.5-6-5.5 0-2 1.4-3.8 2-4.5.4-.4.6-.2.6.3 0 1 .5 2 1.4 2 0-2.5 1-5 4-7.3 0 2 1.2 3.5 2.5 4.5 1.4 1 2.5 2.4 2.5 5C19 18.5 16 21 12 21Z" /></TablerIcon>,
  Sparkles: (p) => <TablerIcon {...p}><path d="m12 3 1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7Z" /><path d="m19 14 .8 2L22 17l-2.2 1L19 20l-.8-2L16 17l2.2-1Z" /></TablerIcon>,
  Activity: (p) => <TablerIcon {...p}><path d="M3 12h4l3-8 4 16 3-8h4" /></TablerIcon>,
  ChartBar: (p) => <TablerIcon {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></TablerIcon>,
  ChartLine: (p) => <TablerIcon {...p}><path d="M3 3v18h18" /><path d="m6 17 4-5 4 3 5-7" /></TablerIcon>,
  ChartPie: (p) => <TablerIcon {...p}><path d="M12 3v9h9" /><path d="M21 12a9 9 0 1 1-9-9" /></TablerIcon>,
  Database: (p) => <TablerIcon {...p}><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></TablerIcon>,
  Download: (p) => <TablerIcon {...p}><path d="M12 4v12M7 11l5 5 5-5M5 20h14" /></TablerIcon>,
  Shield: (p) => <TablerIcon {...p}><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6Z" /></TablerIcon>,
  Edit: (p) => <TablerIcon {...p}><path d="M4 20h4l10-10-4-4L4 16Z" /><path d="m13.5 6.5 4 4" /></TablerIcon>,
  Trash: (p) => <TablerIcon {...p}><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" /></TablerIcon>,
  Dot: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" /></TablerIcon>,
  More: (p) => <TablerIcon {...p}><circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" /></TablerIcon>,
  AlertCircle: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" /></TablerIcon>,
  Info: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 16v-4M12 8h.01" /></TablerIcon>,
  Calendar: (p) => <TablerIcon {...p}><rect x="4" y="5" width="16" height="16" rx="1" /><path d="M16 3v4M8 3v4M4 10h16" /></TablerIcon>,
  Clock: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></TablerIcon>,
  Hash: (p) => <TablerIcon {...p}><path d="M4 9h16M4 15h16M10 3 8 21M16 3l-2 18" /></TablerIcon>,
  Plug: (p) => <TablerIcon {...p}><path d="M9 2v4M15 2v4M7 6h10v5a5 5 0 0 1-10 0Z" /><path d="M12 16v6" /></TablerIcon>,
  Brain: (p) => <TablerIcon {...p}><path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1 6 3 3 0 0 0 1 5 3 3 0 0 0 3 2 3 3 0 0 0 6 0 3 3 0 0 0 3-2 3 3 0 0 0 1-5 3 3 0 0 0-1-6 3 3 0 0 0-3-3 3 3 0 0 0-6 0Z" /><path d="M12 4v18" /></TablerIcon>,
  Mood: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="9" /><circle cx="9" cy="10" r=".5" fill="currentColor" /><circle cx="15" cy="10" r=".5" fill="currentColor" /><path d="M9 15c1 1 2 1.5 3 1.5s2-.5 3-1.5" /></TablerIcon>,
  MoodAngry: (p) => <TablerIcon {...p}><circle cx="12" cy="12" r="9" /><path d="m7 9 2 1M17 9l-2 1" /><path d="M8.5 16c1-1.5 5-1.5 7 0" /></TablerIcon>,
  Adjustments: (p) => <TablerIcon {...p}><path d="M4 6h6M14 6h6M4 12h2M10 12h10M4 18h12M20 18h0" /><circle cx="12" cy="6" r="2" /><circle cx="8" cy="12" r="2" /><circle cx="18" cy="18" r="2" /></TablerIcon>,
  Sliders: (p) => <TablerIcon {...p}><path d="M5 3v18M19 3v18" /><circle cx="5" cy="8" r="2" /><circle cx="19" cy="14" r="2" /></TablerIcon>,
  Crown: (p) => <TablerIcon {...p}><path d="m3 8 4 4 5-7 5 7 4-4-2 11H5Z" /></TablerIcon>,
};

window.Icons = Icons;
