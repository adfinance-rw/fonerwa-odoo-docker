# Rwanda Green Fund Branding Module

This module applies the official Rwanda Green Fund brand colors throughout the entire Odoo interface.

## Brand Colors

### Primary Colors (Main Palette)
- **Rich Black** (#013f41) - 60% usage
  - Primary navigation bars
  - Primary buttons
  - Headers and main UI elements

- **Garden Glow** (#7faf81) - 20% usage
  - Secondary buttons
  - Active states
  - Success messages
  - Hover effects

- **Bleached Jade** (#e0e5d1) - 20% usage
  - Background accents
  - Light sections
  - Table headers
  - Form backgrounds

### Supporting Colors
- **Black** (#000000)
- **Black Box** (#102c2d) - Dark variant
- **Mourn Mountain Snow** (#e9ebeb) - Light grey
- **Cambridge Blue** (#a4c4ac) - Info color
- **Sagebrush** (#947352) - Warning color
- **Tetsu Iron** (#465765) - Alternative dark
- **Birch Beige** (#dac3a2) - Neutral accent

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list: `Settings > Apps > Update Apps List`
3. Search for "Rwanda Green Fund Branding"
4. Click "Install"

## Features

### Backend (Enterprise/Community)
- Custom navigation bar colors
- Branded buttons and forms
- Custom table and list view styling
- Kanban view color schemes
- Modal and dialog styling
- Form status bars
- Calendar view colors
- Chatter/mail styling

### Frontend (Portal/Website)
- Portal navigation styling
- Custom button colors
- Card and panel styling
- Form and input styling
- Table styling
- Alert and badge colors

## CSS Files

- `rgf_backend.css` - Backend/Enterprise interface styling
- `rgf_frontend.css` - Portal/Website styling

## Customization

To further customize colors, edit the CSS variables in the `:root` section of each CSS file:

```css
:root {
    --rgf-rich-black: #013f41;
    --rgf-garden-glow: #7faf81;
    --rgf-bleached-jade: #e0e5d1;
    /* ... more colors */
}
```

## Compatibility

- Odoo 15.0+
- Odoo 16.0+
- Odoo 17.0+

## License

LGPL-3

## Credits

© 2023 Rwanda Green Fund. All rights reserved.

