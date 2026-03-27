# Google Stitch Prompt for adwatch Dashboard UI Improvements

## Project Context

adwatch is a BLE (Bluetooth Low Energy) advertisement analyzer with a real-time web dashboard. The frontend is a single-page app built with Preact + htm (tagged template literals), served as a single `index.html` file. It uses a dark theme with CSS custom properties (--bg, --cyan, --purple, --green, --red, --amber, etc.) and Google Fonts (Inter for UI, JetBrains Mono for code/hex). The dashboard connects to a FastAPI backend via REST APIs and a WebSocket at /ws for real-time streaming.

The UI has these main views:
- **Overview**: Summary cards showing device counts by category (phones, trackers, sensors, etc.) and a live feed table of incoming BLE advertisements
- **Plugin tabs**: Per-protocol views (e.g. ThermoPro sensor readings, Tile tracker sightings) with device-specific data tables
- **Protocol Explorer**: A filterable table of all captured advertisements with faceted search (by type, company ID, service UUID, MAC prefix)
- **Hex Viewer**: A byte-level hex viewer with a visual field editor overlay — users highlight byte ranges, assign names/types, and build protocol specs
- **Spec Manager**: Save/load protocol specs, auto-match specs to advertisements, and generate Python parser plugin code from specs

## Design System

Current CSS variables:
```css
--bg: #0a0a0f;
--bg2: #12121a;
--bg3: #1a1a28;
--glass: rgba(255,255,255,.04);
--glass-border: rgba(255,255,255,.08);
--text: #e0e0e8;
--text2: #888;
--text3: #555;
--cyan: #00e5ff;
--purple: #b388ff;
--green: #69f0ae;
--red: #ff5252;
--amber: #ffd740;
--radius: 12px;
```

Font stack: Inter for body, JetBrains Mono for monospace (hex dumps, MAC addresses, code).

## Components I Need

### 1. Toast Notification System

I need a toast/snackbar notification component for surfacing errors and success messages. Currently all `fetch().catch()` calls silently swallow errors.

Requirements:
- Slides in from the bottom-right corner
- Color-coded by severity: success (--green), error (--red), warning (--amber), info (--cyan)
- Auto-dismisses after 5 seconds with a subtle progress bar
- Can be manually dismissed with an X button
- Stacks multiple toasts vertically
- Uses the glassmorphism style (semi-transparent background with border) matching the existing card design
- Smooth enter/exit animations
- Preact-compatible (functional component with hooks)

### 2. Skeleton Loading States

The app currently shows blank/empty areas while data loads. I need skeleton placeholder components for:

- **Card skeleton**: Matches the summary card dimensions (180px min-width, 20px padding). Show a pulsing rectangle for the value (32px height) and a smaller one for the label (12px height).
- **Table skeleton**: Matches the feed table layout. Show 8-10 rows of pulsing rectangles matching column widths.
- **Hex viewer skeleton**: A grid of pulsing cells matching the 16-column hex layout.

Requirements:
- Pulsing animation using the existing CSS variable colors (subtle shift between --glass and a slightly brighter variant)
- Smooth fade-out transition when real content loads in
- Match the exact dimensions of the real components so there's no layout shift

### 3. Confirmation Dialog / Modal

For destructive actions (delete spec, delete field). Currently these fire immediately with no confirmation.

Requirements:
- Centered modal with backdrop blur overlay
- Title, message body, Cancel and Confirm buttons
- Confirm button is red (--red) for destructive actions
- Escape key and backdrop click dismiss the dialog
- Focus trap while open
- Glassmorphism card style matching existing design
- Returns a promise (or calls a callback) with the user's choice
- Preact-compatible

### 4. WebSocket Connection Status Indicator

Replace the current simple green dot with a smarter connection indicator.

Requirements:
- Three states: Connected (green pulsing dot, current behavior), Reconnecting (amber pulsing dot with "Reconnecting..." text), Disconnected (red static dot with "Offline" text)
- When disconnected, show a subtle banner at the top of the page: "Connection lost. Retrying..." with a manual "Retry Now" button
- Smooth transitions between states
- Compact design that fits in the existing header bar

## Technical Constraints

- Must work as inline `<script type="module">` in a single HTML file
- Uses Preact (imported from esm.sh CDN), NOT React
- Uses htm tagged template literals, NOT JSX: `html\`<div class="foo">${content}</div>\``
- All CSS should use the existing CSS custom properties listed above
- No build step — everything runs directly in the browser
- Components should be self-contained (CSS + JS together) since this is a single-file app
