# Rwanda Green Fund Branding Module

This module applies the official Rwanda Green Fund (RGF) brand colors and styling throughout the Odoo 18 interface, with full support for both light and dark modes.

## 🎨 Brand Colors

### Primary Colors (60-20-20 Rule)
- **Rich Black (#013f41)** - 60%
- **Garden Glow (#7faf81)** - 20%
- **Bleached Jade (#e0e5d1)** - 20%

### Supporting Colors
- Black (#000000)
- Black Box (#102c2d)
- Mourn Snow (#e9ebeb)
- Cambridge Blue (#a4c4ac)
- Sagebrush (#947352)
- Tetsu Iron (#465765)
- Birch Beige (#dac3a2)

## 🏗️ Architecture

This module follows **Odoo's SCSS inheritance best practices** for proper variable override compilation:

### Asset Bundles (Load Order)
1. **`web.dark_mode_variables`** - Dark mode SCSS variable overrides (loaded first)
2. **`web._assets_primary_variables`** - Light mode SCSS variable overrides (loaded early)
3. **`web.assets_backend`** - Backend CSS styling (loaded after variables)
4. **`web.assets_frontend`** - Frontend/Portal CSS styling

### File Structure
```
rgf_branding/
├── static/src/
│   ├── scss/
│   │   ├── dark_mode_variables.scss    # Dark mode variable overrides
│   │   └── light_mode_variables.scss   # Light mode variable overrides
│   └── css/
│       ├── rgf_backend.css             # Backend styling
│       └── rgf_frontend.css            # Frontend/Portal styling
```

## 🌗 Dark Mode Support

### How It Works
- **Light Mode**: Full RGF branding with all custom colors applied
- **Dark Mode**: Uses Odoo's default dark theme for optimal contrast and readability
  - Only the **primary brand color (#013f41)** is overridden
  - All other colors use Odoo's tested dark mode palette

### Why This Approach?
Following [Odoo's SCSS documentation](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/scss_inheritance.html):
- SCSS variables are compiled in a specific order
- Overrides must be in the correct asset bundle to take effect
- Using `web.dark_mode_variables` ensures dark mode customizations compile first
- Using `html.o_dark` selector (not `body.o_dark`) matches Odoo's standard

## 📦 Installation

1. Place the module in your addons directory
2. Update the module list:
   ```bash
   python3 odoo-bin -u rgf_branding -d your_database --dev=all
   ```
3. Clear browser cache and do a hard refresh (`Ctrl+Shift+R`)
4. If needed, regenerate assets from the developer menu

## 🎯 What Gets Branded

### Backend (Odoo Interface)
- Top navigation bar
- Sidebar menus
- Buttons (primary, secondary, success, info)
- Form views and status bars
- List views (tables)
- Kanban cards
- Search panels
- Modals and dropdowns
- Badges and tags
- Progress bars

### Frontend (Portal/Website)
- Website header and navigation
- Portal layout and sidebar
- Cards and tables
- Forms and buttons
- Alerts and badges
- Footer

## 🔧 Customization

To change colors, edit:
- **Light mode**: `static/src/scss/light_mode_variables.scss`
- **Dark mode**: `static/src/scss/dark_mode_variables.scss`

Then upgrade the module with asset regeneration:
```bash
python3 odoo-bin -u rgf_branding -d your_database --dev=assets
```

## 📋 Requirements

- Odoo 18.0+
- `web` module (core)
- `base` module (core)

## 📝 License

LGPL-3

## 👤 Author

Rwanda Green Fund
Website: https://www.fonerwa.org

## 🆕 Version History

### v2.0
- Restructured to use Odoo's SCSS inheritance system properly
- Added SCSS variable overrides in correct asset bundles
- Changed selectors to use `html.o_dark` (Odoo standard)
- Improved dark mode compatibility

### v1.0
- Initial release with RGF branding
- Light mode support
