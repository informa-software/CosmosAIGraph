# Office Add-in for Contract Intelligence Workbench

This is a separate Angular application designed to run as an Office Add-in within Word, Excel, PowerPoint, and other Office applications.

## Project Overview

**Port**: 4201 (to avoid conflicts with the main query-builder app on port 4200)
**Routing**: Hash-based routing (required for Office add-ins due to iframe sandboxing)
**Office.js**: Loaded globally and required for all Office integration

## Architecture

- **Separate from main app**: Independent Angular project with its own dependencies
- **Hash routing**: Uses `withHashLocation()` for Office compatibility
- **Auto-routing**: Automatically routes to the appropriate component based on Office host
- **Extensible**: Designed to support Word, Excel, PowerPoint, and more

## Development Setup

### Prerequisites

1. **HTTPS Certificates**: Required for Office Add-ins
   ```powershell
   # Run from parent directory (impl/)
   .\setup-https-cert.ps1
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

### Running the Add-in

```bash
npm start
# This runs: ng serve --ssl --port 4201
```

The app will be available at: `https://localhost:4201`

### Sideloading in Office

1. **Open Word** (or other Office application)
2. Go to **Insert → Add-ins → My Add-ins**
3. Click **Shared Folder** tab
4. Select `manifest.xml` from this directory
5. The add-in will appear in the **Home** ribbon under **Compliance**

## Project Structure

```
office-addin/
├── src/
│   ├── app/
│   │   ├── home/              # Landing page component
│   │   ├── word-addin/        # Word-specific functionality
│   │   ├── app.ts             # Root component with auto-routing
│   │   ├── app.config.ts      # App config with hash routing
│   │   └── app.routes.ts      # Route definitions
│   ├── index.html             # Loads Office.js globally
│   ├── main.ts                # Waits for Office.onReady()
│   └── styles.scss            # Global styles
├── manifest.xml               # Office Add-in manifest
├── package.json
└── README.md
```

## Routes

- `/#/` → Redirects to `/home`
- `/#/home` → Home page (shows Office context info)
- `/#/word` → Word add-in functionality
- (Future: `/#/excel`, `/#/powerpoint`, etc.)

## Auto-Routing Logic

The app automatically detects the Office host and routes accordingly:

```typescript
Office.context.host === Office.HostType.Word → /word
Office.context.host === Office.HostType.Excel → /excel (future)
Office.context.host === Office.HostType.PowerPoint → /powerpoint (future)
```

## Key Differences from Main App

| Feature | Main App (query-builder) | Office Add-in |
|---------|--------------------------|---------------|
| Port | 4200 | 4201 |
| Routing | Standard (`/route`) | Hash-based (`/#/route`) |
| Office.js | Not loaded | Loaded globally |
| Context | Standalone browser | Office iframe |
| Bootstrap | Immediate | After Office.onReady() |

## Development Notes

### Office.js Integration

- **Loaded in index.html**: `<script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js">`
- **Initialized in main.ts**: Waits for `Office.onReady()` before bootstrapping Angular
- **Hash routing required**: Office sandboxing prevents standard browser routing

### Testing Outside Office

The app can run in a standalone browser for development:
- `https://localhost:4201` → Shows home page with "Not in Office context" message
- Office.js will be loaded but `Office.context` will be undefined
- Useful for UI development and testing

## Future Enhancements

- [ ] Excel add-in component
- [ ] PowerPoint add-in component
- [ ] Shared services between Office apps
- [ ] API integration for contract analysis
- [ ] Document annotation and highlighting
- [ ] Real-time compliance checking

## Building for Production

```bash
npm run build
# Output: dist/office-addin/
```

Update manifest.xml URLs to point to your production server.

## Troubleshooting

**Error: "Office.js not loaded"**
- Ensure Office.js script tag is in index.html
- Check browser console for loading errors
- Verify HTTPS is working

**Error: "Routing not working"**
- Ensure hash-based routing is configured
- Check that routes use `/#/` prefix
- Verify manifest.xml points to correct URLs

**Add-in not appearing in Word**
- Check manifest.xml path in Shared Folder settings
- Verify app is running on https://localhost:4201
- Clear Office cache: Delete `%LOCALAPPDATA%\Microsoft\Office\16.0\Wef\`

## Related Documentation

- [Office Add-ins Documentation](https://learn.microsoft.com/en-us/office/dev/add-ins/)
- [Word JavaScript API](https://learn.microsoft.com/en-us/office/dev/add-ins/reference/overview/word-add-ins-reference-overview)
- [Angular Router](https://angular.dev/guide/routing)
