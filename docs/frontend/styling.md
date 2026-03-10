---
title: Styling Conventions
---

# Styling Conventions

The frontend uses **Tailwind CSS via CDN** for utility-first styling with a set of custom CSS classes for application-specific patterns.

## Tailwind CSS Setup

Tailwind is loaded via CDN script tag:

```html
<script src="https://cdn.tailwindcss.com"></script>
```

The `dark:` variant is used throughout for dark mode support. Theme switching is managed by the `useTheme` hook, which toggles the `dark` class on the document root.

## Color Palette

| Token | Hex | Usage |
|---|---|---|
| Dark background | `#0B0C10` | Primary background in dark mode |
| Light background | `#FBFBFC` | Primary background in light mode |
| Lime green accent | `#D4FF3B` | Primary accent color, CTAs, highlights |

The lime green accent (`#D4FF3B`) is the signature brand color used for primary buttons, active states, agent message highlights, and interactive elements.

## Custom CSS Classes

### .glass-panel

Glassmorphism blur effect for panel backgrounds.

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

Used for card surfaces, sidebars, and overlay panels. Creates a frosted glass appearance that lets background content subtly show through.

### .agent-glow

Lime green glow border applied to agent-related elements.

```css
.agent-glow {
  box-shadow: 0 0 20px rgba(212, 255, 59, 0.3),
              0 0 40px rgba(212, 255, 59, 0.1);
  border: 1px solid rgba(212, 255, 59, 0.4);
}
```

Applied to the chat panel border, agent message bubbles, and active robot cards to create a distinctive glowing effect using the lime green accent.

### .scrollbar-hide

Hides the scrollbar while maintaining scroll functionality.

```css
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
```

Used on the chat message container and marketplace scroll areas for a cleaner visual appearance.

### .fab-pulse

Pulsing animation for the mobile chat floating action button.

```css
@keyframes fab-pulse {
  0% { box-shadow: 0 0 0 0 rgba(212, 255, 59, 0.5); }
  70% { box-shadow: 0 0 0 12px rgba(212, 255, 59, 0); }
  100% { box-shadow: 0 0 0 0 rgba(212, 255, 59, 0); }
}

.fab-pulse {
  animation: fab-pulse 2s infinite;
}
```

Activated on the ChatFAB when there are unread messages to draw user attention.

## Spacing and Shape Patterns

Consistent spacing and border radius patterns are used across the application:

| Pattern | Value | Usage |
|---|---|---|
| Panel border radius | `rounded-[2.5rem]` | Main content panels, cards |
| Button border radius | `rounded-2xl` | Buttons, chips, tags |
| Desktop padding | `p-12` | Main panel internal padding |
| Mobile padding | `p-4` | Mobile layout padding |
| Component gap | `gap-4` / `gap-6` | Spacing between sibling elements |

## Dark Mode

All components use Tailwind's `dark:` variant for dark mode styling. The pattern follows:

```html
<div class="bg-[#FBFBFC] dark:bg-[#0B0C10] text-gray-900 dark:text-gray-100">
  <!-- content -->
</div>
```

The `useTheme` hook manages the `dark` class on the `<html>` element, and all components should include `dark:` variants for background, text, and border colors.

## Conventions

- Always include `dark:` variants for any color-related utility classes
- Use the lime green accent (`#D4FF3B`) for primary interactive elements and agent-related visuals
- Prefer Tailwind utilities over inline styles
- Custom classes (`.glass-panel`, `.agent-glow`, etc.) are defined in the global stylesheet for patterns that cannot be expressed as single utilities
- Use `!important` on custom CSS properties that may be overridden by Tailwind or Flowbite base styles (e.g., heading and body resets)
