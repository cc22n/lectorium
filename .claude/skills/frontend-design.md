# Skill: Frontend — Patrones de diseno

## Stack frontend
- Django Templates con herencia (base.html -> page.html)
- Tailwind CSS via CDN (no compilado)
- HTMX para interacciones dinamicas
- Minimal JavaScript vanilla cuando sea necesario

## Filosofia de diseno
Minimalista y limpio. Tipografia fuerte, espaciado generoso, colores sutiles.
Nada de gradientes, sombras pesadas o decoraciones innecesarias.

## Tipografia
- **Headings:** Source Serif 4 (serif) — elegante, literario
- **Body:** DM Sans (sans-serif) — limpio, legible
- Cargadas via Google Fonts en base.html

## Paleta de colores (CSS en tailwind.config)
```
ink:        #1a1a2e   (texto principal, botones primarios)
parchment:  #faf8f5   (fondo principal)
warm:       #f5f0eb   (fondo alternativo, hovers)
accent:     #c7956d   (acentos, links activos)
accent-dark:#a87a55   (hover de acentos)
muted:      #8c8c8c   (texto secundario)
subtle:     #e8e4df   (bordes, divisores)
```

## Estructura de templates
```
templates/
  base.html               # Layout principal (nav, messages, footer)
  includes/
    navbar.html            # Navegacion (responsive)
    club_card.html         # Card reutilizable para clubes
  accounts/
    login.html
    register.html
    profile.html
    edit_profile.html
  clubs/
    home.html              # Landing
    explore.html           # Explorar con filtros
    detail.html            # Detalle de club
    create.html            # Crear club
  books/
    search_results.html    # HTMX partial para busqueda
    manual_create.html     # Registro manual de libro
  reports/
    submit.html            # Entregar reporte
    list.html              # Ver reportes (fase REVIEW)
    detail.html            # Reporte individual con comentarios
```

## Patrones de componentes

### Cards
```html
<div class="bg-white rounded-xl border border-subtle p-5 hover:shadow-md transition-all">
  <!-- contenido -->
</div>
```

### Botones
```html
<!-- Primario -->
<button class="px-6 py-2.5 bg-ink text-white rounded-lg hover:bg-ink/90 transition-colors font-medium">

<!-- Secundario -->
<button class="px-4 py-2 border border-subtle rounded-lg hover:border-ink/30 transition-colors">

<!-- Destructivo -->
<button class="px-4 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors">
```

### Formularios
```html
<input class="w-full border border-subtle rounded-lg px-4 py-2.5 text-sm bg-white focus:outline-none focus:border-accent">
<label class="block text-sm font-medium text-ink mb-1.5">
```

### Status badges
```html
<!-- Usar colores semanticos segun el estado -->
<span class="text-xs font-medium px-2.5 py-1 rounded-full bg-green-50 text-green-700">Abierto</span>
<span class="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-50 text-blue-700">En lectura</span>
```

### Secciones vacias
```html
<div class="bg-white rounded-xl border border-subtle p-8 text-center">
  <p class="text-muted">Mensaje vacio.</p>
  <a href="#" class="text-sm text-accent-dark hover:text-accent mt-2 inline-block">Accion</a>
</div>
```

## HTMX patterns
```html
<!-- Busqueda con debounce -->
<input hx-get="/search/" hx-trigger="keyup changed delay:400ms" hx-target="#results" name="q">

<!-- Form submit -->
<form hx-post="/action/" hx-target="#result" hx-swap="outerHTML">

<!-- Carga parcial -->
<div hx-get="/partial/" hx-trigger="load" hx-swap="innerHTML">
```

## Reglas estrictas
- NO usar frameworks JS (React, Vue, etc.) — solo HTMX + vanilla JS
- NO agregar CDNs adicionales sin justificacion
- NO usar iconos de librerias externas — usar SVGs inline simples
- Mantener consistencia con la paleta de colores existente
- Todos los textos en templates en espanol SIN acentos (limitacion Windows)
- Mobile-first: probar que todo funcione en pantallas pequenas
