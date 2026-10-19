// Configurateur du fichier de menus (docs/menu/menus.md) : apercu de la borne ou l'on clique,
// glisse et redimensionne les boutons, panneau de gauche selon ce qui est choisi (l'ecran ou
// un bouton), fichier menus.yaml. Le fichier ne contient que ce qui change par rapport aux
// menus du jeu (menus/defaults.yaml).
'use strict';
const $ = (id) => document.getElementById(id);
const DATA = MENUS_DATA;
const L = MenusLayout, R = MenusRender;
const LANGS = ['fr', 'en', 'de', 'es', 'it'];
const FILE_MENUS = ['main', 'miscellaneous', 'settings', 'categories'];
const GAME_SCREENS = ['games', 'options', 'players'];
const RESOLUTIONS = [[1024, 600], [1280, 720], [1366, 768], [1600, 900], [1920, 1080], [800, 480]];
const FITS = ['stretch', 'cover', 'contain', 'center', 'tile', 'slice'];
const POSITIONS = ['center', 'top', 'bottom', 'left', 'right', 'top_left', 'top_right', 'bottom_left', 'bottom_right'];
const SHAPES = ['rounded', 'rectangle', 'pill', 'none'];
const THEME_COLORS = ['menu-buttons', 'menu-selected', 'menu-shortcut', 'menu-header', 'menu-text', 'menu-text-black',
  'menu-text-white', 'menu-border', 'menu-alternate', 'menu-ok', 'menu-warning', 'menu-ko', 'menu-inactive', 'menu-favorite'];
const GAME_TILES_AREA = { x: '3.125%', y: '18.75%', width: '40%', height: '62.5%' };

let lang = 'fr';
let user = {};                    // contenu du fichier menus.yaml
let screen = 'main';              // ecran montre et edite
let selected = 1;                 // bouton dessine dans l'etat choisi (ordre affiche)
let selection = { kind: 'screen' };   // ce que montre le panneau : l'ecran, ou {kind: 'button', id}
let scope = 'one';                // aspect : 'one' (ce bouton) ou 'all' (tous les boutons de l'ecran)
let showSelected = false;         // le bouton edite est montre dans l'etat choisi (groupe « Bouton choisi » ouvert)
let fitNotice = false;            // les boutons viennent d'etre reduits pour tenir sur l'ecran
const ownImages = {};             // images chargees : chemin -> URL locale
let ownTheme = null;              // theme charge : {colors, font, images}
let lastDraw = null;              // zones de l'apercu et geometrie des boutons
let history = [], lastState = '{}';   // Ctrl+Z

// ------------------------------------------------------------------ textes
function t(key, values) {
  let text = (T[lang] && T[lang][key]) || T.en[key] || T.fr[key] || key;
  for (const [name, value] of Object.entries(values || {})) text = text.replaceAll(`{${name}}`, value);
  return text;
}
function gameText(key) {
  // Textes du jeu (traductions de locales/*.po) : le texte d'un bouton tel qu'affiche
  const texts = DATA.texts[lang] || {};
  return texts[key] !== undefined ? texts[key] : key;
}
function store(key, value) { try { localStorage.setItem(`raspydarts-menus-${key}`, value); } catch (e) { /* prive */ } }
function stored(key) { try { return localStorage.getItem(`raspydarts-menus-${key}`); } catch (e) { return null; } }

// ------------------------------------------------------------------ donnees du fichier
const clone = (value) => JSON.parse(JSON.stringify(value));
function isEmpty(value) {
  return value === undefined || value === '' || (L.isDict(value) && !Object.keys(value).length);
}
function getPath(object, path) {
  let value = object;
  for (const key of path) { if (!L.isDict(value)) return undefined; value = value[key]; }
  return value;
}
function setPath(object, path, value) {
  // value undefined ou vide : la cle est retiree (et ses parents vides)
  const parents = [object];
  let node = object;
  for (const key of path.slice(0, -1)) {
    if (!L.isDict(node[key])) node[key] = {};
    node = node[key];
    parents.push(node);
  }
  const last = path[path.length - 1];
  if (isEmpty(value)) delete node[last]; else node[last] = value;
  for (let i = path.length - 2; i >= 0; i--) {
    if (L.isDict(parents[i][path[i]]) && !Object.keys(parents[i][path[i]]).length) delete parents[i][path[i]];
  }
}
function merged() { return R.combine(DATA.defaults, user); }
function userMenu(name, create) {
  if (!L.isDict(user.menus)) { if (!create) return {}; user.menus = {}; }
  if (!L.isDict(user.menus[name])) { if (!create) return {}; user.menus[name] = {}; }
  return user.menus[name];
}
function menuButtons(name) {
  // Boutons du menu (tels que le jeu les aura)
  return ((merged().menus || {})[name] || {}).buttons || [];
}
function ownButtons(name) {
  // La liste des boutons dans le fichier (copiee des menus du jeu au premier changement)
  const menu = userMenu(name, true);
  if (!Array.isArray(menu.buttons)) { menu.buttons = clone(menuButtons(name)); delete menu.button_changes; }
  return menu.buttons;
}
function cleanUser() {
  if (L.isDict(user.menus)) {
    for (const [name, menu] of Object.entries(user.menus)) if (!L.isDict(menu) || !Object.keys(menu).length) delete user.menus[name];
    if (!Object.keys(user.menus).length) delete user.menus;
  }
  if (L.isDict(user.styles)) {
    for (const [name, style] of Object.entries(user.styles)) {
      const used = Object.values(user.menus || {}).some(m => L.isDict(m) && (m.style === name || [].concat(m.buttons || []).some(b => L.isDict(b) && b.style === name)));
      if (L.isDict(style) && !Object.keys(style).length && !used) delete user.styles[name];
    }
    if (!Object.keys(user.styles).length) delete user.styles;
  }
}
function screens() {
  const menus = Object.keys(merged().menus || {}).filter(n => !['favorite_save', 'favorite_players', 'favorite_game', 'question'].includes(n));
  const own = menus.filter(n => !FILE_MENUS.includes(n) && !GAME_SCREENS.includes(n));
  return FILE_MENUS.concat(own, GAME_SCREENS);
}
function isLook(text) {
  // Un bloc d'aspect (taille, police...) et non des traductions
  return L.isDict(text) && Object.keys(text).length > 0 && !Object.keys(text).every(k => R.LANGUAGES.includes(k));
}

// ------------------------------------------------------------------ resolution et unites
function reference() { return Array.isArray(user.resolution) ? user.resolution : null; }
function previewSize() {
  const value = $('preview-res').value || '1920x1080';
  return value.split('x').map(Number);
}
// Positions et tailles : en % de l'ecran (placement automatique) ou en pixels de la resolution choisie
function toUnits(value, axis) {
  if (value === undefined || value === null || value === '') return '';
  if (typeof value === 'string' && !value.trim().endsWith('%') && isNaN(parseFloat(value))) return '';   // auto
  if (reference()) return Math.round(new L.Units(reference(), reference()).length(value, axis));
  return Math.round(new L.Units([1, 1], null).length(value, axis) * 10000) / 100;
}
function fromUnits(text) {
  if (text === '' || text === null) return undefined;
  const number = parseFloat(String(text).replace(',', '.'));
  if (isNaN(number)) return undefined;
  return reference() ? Math.round(number) : Math.round(number * 100) / 10000;
}
// Pixels de l'apercu vers les valeurs du fichier (fraction de l'ecran, ou pixels de la resolution)
function pxToFile(px, axis, floor) {
  const [W, H] = previewSize();
  const ref = reference();
  const round = floor ? Math.floor : Math.round;
  if (ref) return round(px * (axis === 'x' ? ref[0] / W : ref[1] / H));
  return round(px / (axis === 'x' ? W : H) * 10000) / 10000;
}

// ------------------------------------------------------------------ menus : boutons et disposition
function themeName() { return $('theme').value || 'remi'; }
function makeRenderer(ctx) {
  const favorites = $('fav-games').checked;
  return new R.Renderer(DATA, merged(), {
    ctx: ctx || { translate: gameText }, language: lang, theme: themeName(), imageUrl: imageUrl, favoriteGames: favorites,
    favoriteList: favorites ? ['Cricket', 'Low_Score'] : [], favorites: {}
  });
}
function menuInfo(name) {
  // Le menu tel que le jeu le compose : ses boutons affiches, ceux du bas, dessin par styles ou non
  const renderer = makeRenderer();
  const menu = renderer.menu(name), items = renderer.items(name);
  const listed = items.filter(b => !R.FOOTERS[b.footer]), footers = items.filter(b => R.FOOTERS[b.footer]);
  return { renderer: renderer, menu: menu, items: items, listed: listed, footers: footers, styled: renderer.styled(name, menu, items) };
}
function metrics(menu, listed) {
  // Les grandeurs de la disposition (comme MenusLayout.layout), en pixels de l'apercu
  const [W, H] = previewSize();
  const units = new L.Units([W, H], reference());
  const kind = String(menu.layout || 'list');
  const defaults = L.LAYOUT_DEFAULTS[kind] || L.LAYOUT_DEFAULTS.list;
  const area = L.merge(defaults.area, menu.area || {});
  const columns = Math.max(1, parseInt(menu.columns || defaults.columns, 10));
  const gap = L.merge(L.GAP_DEFAULT, menu.gap || {});
  const rect = [units.length(area.x, 'x'), units.length(area.y, 'y'), units.length(area.width, 'x'), units.length(area.height, 'y')];
  const gapX = units.length(gap.x, 'x'), gapY = units.length(gap.y, 'y');
  const flowing = listed.filter(b => !b.place);
  // Rangees de la grille (boutons sur plusieurs cases compris)
  const grid = L.layout(menu, listed, [W, H], reference(), 1);
  return { kind: kind, columns: columns, rows: Math.max(1, grid.rows), cells: grid.cells, buttonH: grid.buttonH, area: rect, gapX: gapX, gapY: gapY,
           columnW: (rect[2] - (columns - 1) * gapX) / columns, flowing: flowing, size: L.merge(defaults.button_size, menu.button_size || {}) };
}
function ensureStyled(name) {
  // Le dessin classique du theme ne suit pas la disposition : il passe au dessin par la
  // disposition, qui reprend la place qu'avaient ses boutons (pas de saut a l'ecran)
  const info = menuInfo(name);
  if (info.styled) return;
  const own = userMenu(name, true);
  const geo = name === screen && lastDraw && lastDraw.geometry;
  const rects = geo ? info.listed.map(b => geo.rects[R.buttonId(b)]).filter(Boolean) : [];
  if (!rects.length) {
    const kind = String(info.menu.layout || 'list');
    own.area = clone((L.LAYOUT_DEFAULTS[kind] || L.LAYOUT_DEFAULTS.list).area);
    return;
  }
  const left = Math.min(...rects.map(r => r[0])), top = Math.min(...rects.map(r => r[1]));
  const right = Math.max(...rects.map(r => r[0] + r[2])), bottom = Math.max(...rects.map(r => r[1] + r[3]));
  const first = rects[0];
  const columns = rects.filter(r => Math.abs(r[1] - first[1]) < 2).length;
  const below = rects.find(r => r[1] > first[1] + 2);
  const beside = rects.find(r => Math.abs(r[1] - first[1]) < 2 && r[0] > first[0] + 2);
  own.area = { x: pxToFile(left, 'x'), y: pxToFile(top, 'y'), width: pxToFile(right - left, 'x'), height: pxToFile(bottom - top, 'y') };
  own.button_size = { height: pxToFile(first[3], 'y') };
  own.gap = { y: pxToFile(below ? Math.max(0, below[1] - first[1] - first[3]) : 0, 'y') };
  if (beside) own.gap.x = pxToFile(beside[0] - first[0] - first[2], 'x');
  if (columns > 1) own.columns = columns;
  own.align = 'top';
}
function fitOnScreen(name) {
  // Un ecran reste un seul ecran : si les boutons de la disposition depassent sa zone (pages),
  // leur hauteur est reduite pour qu'ils y tiennent tous
  if (GAME_SCREENS.includes(name)) return false;
  let fitted = false;
  for (let attempt = 0; attempt < 4; attempt++) {
    const info = menuInfo(name);
    if (!info.styled || !info.listed.length) return fitted;
    const m = metrics(info.menu, info.listed);
    const result = L.layout(info.menu, info.listed, previewSize(), reference(), 1);
    const rects = info.listed.map((b, i) => (b.place ? null : result.rects[i + 1])).filter(Boolean);
    const over = result.pages > 1 || rects.some(r => r[1] + r[3] > m.area[1] + m.area[3] + 1 || r[1] < m.area[1] - 1);
    if (!over) return fitted;
    const spaces = m.flowing.reduce((sum, b) => sum + (parseFloat(b.space_before) || 0), 0);
    const height = Math.max(1, (m.area[3] - (m.rows - 1) * m.gapY) / (m.rows + spaces) * (1 - 0.003 * (attempt + 1)));
    const own = userMenu(name, true);
    if (m.size.height === null || m.size.height === undefined) {
      // Tuiles carrees : elles le restent
      setPath(own, ['button_size', 'width'], Math.min(1, Math.floor(height / m.columnW * 1000) / 1000));
    }
    setPath(own, ['button_size', 'height'], pxToFile(height, 'y', true));
    fitted = true;
  }
  return fitted;
}

// ------------------------------------------------------------------ apercu
function imageUrl(path) {
  if (!path) return null;
  const variants = [String(path)];
  if (!String(path).startsWith('images/')) variants.push('images/' + path);
  for (const p of variants) {
    if (ownImages[p]) return ownImages[p];
    if (ownTheme && ownTheme.images[p]) return ownTheme.images[p];
  }
  const owners = themeName() === 'own' ? ['official'] : [themeName(), 'official'];
  for (const p of variants) for (const owner of owners) {
    const url = ((DATA.images || {})[owner] || {})[p];
    if (url) return url;
  }
  return null;
}
function themeSetup() {
  const theme = DATA.themes[themeName() === 'own' ? 'clear' : themeName()];
  let colors = Object.assign({}, theme.colors), font = theme.font, background = theme.background;
  if (themeName() === 'own' && ownTheme) {
    colors = Object.assign(colors, ownTheme.colors);
    if (ownTheme.font) font = ownTheme.font;
    if (ownTheme.images['images/background/background.png']) background = 'images/background/background.png';
  }
  return { colors: colors, font: font, background: background };
}
MenusDraw.fontUrl = (file) => (ownTheme && ownTheme.fonts[file]) || DATA.fonts[file] || null;
MenusDraw.styleDefaults = DATA.styleDefaults;
MenusDraw.setOnLoaded(() => schedule());

let pending = false;
function schedule() { if (!pending) { pending = true; requestAnimationFrame(() => { pending = false; draw(); }); } }
function draw() {
  const canvas = $('preview');
  const [width, height] = previewSize();
  canvas.width = width; canvas.height = height;
  const theme = themeSetup();
  const ctx = new MenusDraw.Context(canvas, {
    width: width, height: height, colors: theme.colors, font: theme.font, themeBackground: theme.background,
    texts: DATA.texts[lang] || {}, imageUrl: imageUrl
  });
  const renderer = makeRenderer(ctx);
  try {
    if (screen === 'games') lastDraw = renderer.drawGames(selected);
    else if (screen === 'options') lastDraw = renderer.drawOptions(selected);
    else if (screen === 'players') lastDraw = renderer.drawPlayers(selected);
    else lastDraw = renderer.draw(screen, selected);
    lastDraw.geometry = geometry();
    $('file-errors').textContent = '';
  } catch (error) {
    $('file-errors').textContent = t('draw-error') + ' ' + error.message;
    console.error(error);
  }
  drawOverlay();
}
function geometry() {
  // Ou sont les boutons de l'ecran (rectangles de la disposition, sans l'agrandissement de
  // l'etat choisi) et sa zone de boutons
  const [W, H] = previewSize();
  if (GAME_SCREENS.includes(screen)) {
    const menu = (merged().menus || {}).games || {};
    if (screen !== 'games' || String(makeRenderer().menu('games').style || 'classic') === 'classic') return { ids: [], rects: {}, area: null };
    const units = new L.Units([W, H], reference());
    const area = L.merge(GAME_TILES_AREA, menu.area || {});
    return { ids: [], rects: {}, area: [units.length(area.x, 'x'), units.length(area.y, 'y'), units.length(area.width, 'x'), units.length(area.height, 'y')] };
  }
  const info = menuInfo(screen);
  const ids = info.listed.concat(info.footers).map(R.buttonId);
  const layout = info.styled ? L.layout(info.menu, info.listed, [W, H], reference(), Math.max(1, Math.min(selected, info.listed.length || 1))).rects : null;
  const rects = {};
  ids.forEach((id, i) => {
    const rect = layout && i < info.listed.length ? layout[i + 1] : lastDraw.zones[i + 1];
    if (rect && !rects[id]) rects[id] = rect;
  });
  return { ids: ids, rects: rects, listed: info.listed.map(R.buttonId), area: info.styled ? metrics(info.menu, info.listed).area : null };
}
function shownIds() { return (lastDraw && lastDraw.geometry && lastDraw.geometry.ids) || []; }

// ------------------------------------------------------------------ calque de selection
let ghost = null;     // taille en cours d'un bouton de la disposition (avant la question)
let dropZone = null;  // zone des boutons ou le bouton glisse sera fixe
let dropCell = null;  // case de la zone visee : {row, column, rect}
let guides = [];      // reperes d'alignement montres pendant un geste : {axis, pos, center}
let hover = null;
function overlayScale() {
  const canvas = $('preview');
  return canvas.width / (canvas.getBoundingClientRect().width || canvas.width);
}
function handles(rect) {
  const [x, y, w, h] = rect;
  return { nw: [x, y], n: [x + w / 2, y], ne: [x + w, y], e: [x + w, y + h / 2], se: [x + w, y + h], s: [x + w / 2, y + h],
           sw: [x, y + h], w: [x, y + h / 2] };
}
function drawOverlay() {
  const overlay = $('overlay'), canvas = $('preview');
  if (overlay.width !== canvas.width || overlay.height !== canvas.height) { overlay.width = canvas.width; overlay.height = canvas.height; }
  const g = overlay.getContext('2d');
  g.clearRect(0, 0, overlay.width, overlay.height);
  const geo = lastDraw && lastDraw.geometry;
  if (!geo) return;
  const s = overlayScale();
  const frame = (rect, color, width, dash) => {
    g.save();
    g.setLineDash(dash ? [8 * s, 5 * s] : []);
    g.lineWidth = (width + 2) * s; g.strokeStyle = 'rgba(0,0,0,0.65)';
    g.strokeRect(rect[0], rect[1], rect[2], rect[3]);
    g.lineWidth = width * s; g.strokeStyle = color;
    g.strokeRect(rect[0], rect[1], rect[2], rect[3]);
    g.restore();
  };
  const knobs = (rect) => {
    const side = 9 * s;
    for (const [x, y] of Object.values(handles(rect))) {
      g.fillStyle = '#ffffff'; g.fillRect(x - side / 2, y - side / 2, side, side);
      g.lineWidth = 2 * s; g.strokeStyle = '#0a84ff'; g.strokeRect(x - side / 2, y - side / 2, side, side);
    }
  };
  if (hover && !(selection.kind === 'button' && selection.id === hover) && geo.rects[hover]) frame(geo.rects[hover], 'rgba(255,255,255,0.7)', 1, false);
  if (selection.kind === 'button' && geo.rects[selection.id]) {
    const rect = geo.rects[selection.id];
    frame(rect, '#0a84ff', 3, false);
    if (resizable(selection.id)) knobs(rect);
  } else if (selection.kind === 'screen' && geo.area) {
    frame(geo.area, '#ffd60a', 2, true);
    knobs(geo.area);
  }
  if (ghost) {
    frame(ghost, '#ffd60a', 2, true);
    if (ghost.label) {
      g.font = `bold ${Math.round(16 * s)}px system-ui, sans-serif`;
      const w = g.measureText(ghost.label).width + 12 * s;
      g.fillStyle = 'rgba(0,0,0,0.75)'; g.fillRect(ghost[0], ghost[1] - 26 * s, w, 24 * s);
      g.fillStyle = '#ffd60a'; g.fillText(ghost.label, ghost[0] + 6 * s, ghost[1] - 8 * s);
    }
  }
  if (dropZone) frame(dropZone, '#30d158', 3, true);
  if (dropCell) {
    g.fillStyle = 'rgba(48,209,88,0.35)';
    g.fillRect(...dropCell.rect);
    frame(dropCell.rect, '#30d158', 3, false);
  }
  // Reperes d'alignement (comme un editeur d'interface) : centre de l'ecran en cyan
  for (const guide of guides) {
    g.save();
    g.lineWidth = 2 * s;
    g.strokeStyle = guide.center ? '#00e5ff' : '#ff2d95';
    g.setLineDash(guide.center ? [10 * s, 6 * s] : []);
    g.beginPath();
    if (guide.axis === 'x') { g.moveTo(guide.pos, 0); g.lineTo(guide.pos, overlay.height); }
    else { g.moveTo(0, guide.pos); g.lineTo(overlay.width, guide.pos); }
    g.stroke();
    if (guide.center) {
      g.font = 'bold ' + Math.round(14 * s) + 'px system-ui, sans-serif';
      g.fillStyle = '#00e5ff';
      if (guide.axis === 'x') g.fillText(t('guide-center'), guide.pos + 6 * s, 18 * s);
      else g.fillText(t('guide-center'), 6 * s, guide.pos - 6 * s);
    }
    g.restore();
  }
}
function canvasPoint(event) {
  const canvas = $('preview');
  const box = canvas.getBoundingClientRect();
  return [(event.clientX - box.left) * canvas.width / box.width, (event.clientY - box.top) * canvas.height / box.height];
}
const inside = (p, r, margin) => p[0] >= r[0] - (margin || 0) && p[0] <= r[0] + r[2] + (margin || 0) && p[1] >= r[1] - (margin || 0) && p[1] <= r[1] + r[3] + (margin || 0);
function handleAt(rect, point) {
  const reach = 9 * overlayScale();
  for (const [name, [x, y]] of Object.entries(handles(rect))) if (Math.abs(point[0] - x) <= reach && Math.abs(point[1] - y) <= reach) return name;
  return null;
}
function onEdge(rect, point) {
  const reach = 7 * overlayScale();
  return inside(point, rect, reach) && !inside(point, [rect[0] + reach, rect[1] + reach, rect[2] - 2 * reach, rect[3] - 2 * reach]);
}
function buttonAt(point) {
  const geo = lastDraw && lastDraw.geometry;
  if (!geo) return null;
  const ids = geo.ids.slice().sort((a, b) => (b === currentId()) - (a === currentId()));
  for (const id of ids) if (geo.rects[id] && inside(point, geo.rects[id])) return id;
  return null;
}
function currentId() { return selection.kind === 'button' ? selection.id : null; }
function buttonOf(id) { return menuButtons(screen).find(b => R.buttonId(b) === id); }
function isFooter(id) { const b = buttonOf(id); return !!(b && R.FOOTERS[b.footer]); }
function resizable(id) { return !GAME_SCREENS.includes(screen) && !isFooter(id) && !!buttonOf(id); }
function isFree(id) { const b = buttonOf(id); return !!(b && L.isDict(b.place)); }
const CURSORS = { nw: 'nwse-resize', se: 'nwse-resize', ne: 'nesw-resize', sw: 'nesw-resize', n: 'ns-resize', s: 'ns-resize', e: 'ew-resize', w: 'ew-resize' };

function setPlace(id, rect) {
  // Le bouton place librement a ce rectangle (son point d'ancrage garde)
  editButton(id, b => {
    const place = L.isDict(b.place) ? b.place : {};
    const anchor = L.ANCHORS[String(place.anchor || 'top_left')] || [0, 0];
    b.place = Object.assign({}, place, {
      x: pxToFile(rect[0] + anchor[0] * rect[2], 'x'), y: pxToFile(rect[1] + anchor[1] * rect[3], 'y'),
      width: pxToFile(rect[2], 'x'), height: pxToFile(rect[3], 'y')
    });
  });
}
function cellsFor(rect) {
  // Nombre entier de colonnes et de rangees de la disposition le plus proche de ce rectangle
  const info = menuInfo(screen);
  const m = metrics(info.menu, info.listed);
  const stepX = m.columnW + m.gapX, stepY = m.buttonH + m.gapY;
  const baseW = (info.styled ? m.columnW * parseFloat(m.size.width || 1) : m.columnW);
  return [Math.max(1, Math.round((rect[2] - baseW) / stepX) + 1), Math.max(1, Math.round((rect[3] - m.buttonH) / stepY) + 1)];
}
function setArea(rect) {
  setPath(userMenu(screen, true), ['area'], { x: pxToFile(rect[0], 'x'), y: pxToFile(rect[1], 'y'), width: pxToFile(rect[2], 'x'), height: pxToFile(rect[3], 'y') });
}
function resized(rect, handle, dx, dy) {
  const [W, H] = previewSize();
  let [x, y, w, h] = rect;
  const minW = W * 0.03, minH = H * 0.03;
  if (handle.includes('w')) { x += dx; w -= dx; }
  if (handle.includes('e')) w += dx;
  if (handle.includes('n')) { y += dy; h -= dy; }
  if (handle.includes('s')) h += dy;
  if (w < minW) { if (handle.includes('w')) x -= minW - w; w = minW; }
  if (h < minH) { if (handle.includes('n')) y -= minH - h; h = minH; }
  return [Math.round(x), Math.round(y), Math.round(w), Math.round(h)];
}
const clamp = (v, low, high) => Math.max(low, Math.min(high, v));

let op = null;   // ce que fait la souris : move, resize, area
$('overlay').addEventListener('pointerdown', (event) => {
  if (event.button !== 0) return;
  $('overlay').focus();
  const point = canvasPoint(event);
  const geo = lastDraw && lastDraw.geometry;
  if (!geo) return;
  const id = currentId();
  if (id && geo.rects[id] && resizable(id)) {
    const handle = handleAt(geo.rects[id], point);
    if (handle) {
      // Un ecran au dessin classique passe a la disposition des le debut (les cases montrees
      // sont alors justes) ; Annuler le remet comme avant
      const before = JSON.stringify(user);
      if (!isFree(id)) ensureStyled(screen);
      op = { type: 'resize', id: id, handle: handle, start: point, rect: geo.rects[id].slice(), free: isFree(id), before: before };
      capture(event); return;
    }
  }
  if (selection.kind === 'screen' && geo.area) {
    const handle = handleAt(geo.area, point);
    if (handle) { op = { type: 'area', handle: handle, start: point, rect: geo.area.slice(), size: clone(userMenu(screen).button_size || null) }; capture(event); return; }
  }
  if (GAME_SCREENS.includes(screen)) {
    // Ecran du jeu : ses boutons montrent leur aspect choisi, le panneau reste celui de l'ecran
    for (const [index, rect] of Object.entries(lastDraw.zones || {})) if (rect && inside(point, rect)) { selected = Number(index); schedule(); break; }
    if (selection.kind !== 'screen') selectScreen();
    return;
  }
  const hit = buttonAt(point);
  if (hit) {
    if (hit !== id) selectButton(hit);
    if (resizable(hit) && geo.rects[hit]) { op = { type: 'move', id: hit, start: point, rect: geo.rects[hit].slice(), started: false }; capture(event); }
    return;
  }
  if (selection.kind === 'screen' && geo.area && onEdge(geo.area, point)) {
    op = { type: 'area', handle: 'move', start: point, rect: geo.area.slice(), size: clone(userMenu(screen).button_size || null) }; capture(event); return;
  }
  if (selection.kind !== 'screen') selectScreen();
});
function capture(event) { try { $('overlay').setPointerCapture(event.pointerId); } catch (e) { /* ancien navigateur */ } }
$('overlay').addEventListener('pointermove', (event) => {
  const point = canvasPoint(event);
  const [W, H] = previewSize();
  if (!op) {
    // Curseur : poignees, bord de la zone, bouton a deplacer
    const geo = lastDraw && lastDraw.geometry;
    if (!geo) return;
    let cursor = 'default';
    const id = currentId();
    const handle = (id && geo.rects[id] && resizable(id) && handleAt(geo.rects[id], point)) ||
                   (selection.kind === 'screen' && geo.area && handleAt(geo.area, point));
    const over = GAME_SCREENS.includes(screen) ? null : buttonAt(point);
    if (handle) cursor = CURSORS[handle];
    else if (over && resizable(over)) cursor = 'move';
    else if (over) cursor = 'pointer';
    else if (selection.kind === 'screen' && geo.area && onEdge(geo.area, point)) cursor = 'move';
    $('overlay').style.cursor = cursor;
    if (over !== hover) { hover = over; drawOverlay(); }
    return;
  }
  const dx = point[0] - op.start[0], dy = point[1] - op.start[1];
  if (op.type === 'move') {
    if (!op.started) {
      if (Math.hypot(dx, dy) < 4 * overlayScale()) return;
      op.started = true;
      ensureStyled(screen);
      const info = menuInfo(screen);
      op.area = metrics(info.menu, info.listed).area;
    }
    let rect = [Math.round(clamp(op.rect[0] + dx, 0, W - op.rect[2])), Math.round(clamp(op.rect[1] + dy, 0, H - op.rect[3])), op.rect[2], op.rect[3]];
    // Lache dans la zone des boutons : il sera fixe sur la case visee (en vert) ; ailleurs
    // il est place librement, aimante par les reperes d'alignement
    op.drop = [rect[0] + rect[2] / 2, rect[1] + rect[3] / 2];
    if (inside(op.drop, op.area)) {
      dropZone = op.area;
      dropCell = cellAt(op.drop, op.id);
      guides = [];
    } else {
      dropZone = dropCell = null;
      rect = snap(rect, 'move', [op.id], event.altKey);
    }
    setPlace(op.id, rect);
    schedule();
  } else if (op.type === 'resize') {
    op.current = snap(resized(op.rect, op.handle, dx, dy), op.handle, [op.id], event.altKey);
    if (op.free) { setPlace(op.id, op.current); schedule(); } else {
      // Montre combien de cases de la disposition il prendrait seul (reponse « Non »)
      const [c, r] = cellsFor(op.current);
      ghost = op.current.slice();
      ghost.label = t('span-label', { c: c, r: r });
      drawOverlay();
    }
  } else if (op.type === 'area') {
    op.moved = true;
    let rect = op.handle === 'move' ? [Math.round(clamp(op.rect[0] + dx, 0, W - op.rect[2])), Math.round(clamp(op.rect[1] + dy, 0, H - op.rect[3])), op.rect[2], op.rect[3]]
      : resized(op.rect, op.handle, dx, dy);
    // La zone s'aligne sur l'ecran et sur les boutons places librement (pas sur les siens)
    const inArea = (lastDraw.geometry.listed || []).filter(id => !isFree(id));
    rect = snap(rect, op.handle, inArea, event.altKey, true);
    if (screen === 'games') setPath(userMenu('games', true), ['area'], { x: pxToFile(rect[0], 'x'), y: pxToFile(rect[1], 'y'), width: pxToFile(rect[2], 'x'), height: pxToFile(rect[3], 'y') });
    else {
      // Les boutons suivent la zone pendant qu'on la tire : leur taille d'avant, reduite
      // si elle ne tient plus (jamais de deuxieme page)
      setPath(userMenu(screen, true), ['button_size'], op.size ? clone(op.size) : undefined);
      setArea(rect);
      fitNotice = fitOnScreen(screen);
    }
    schedule();
  }
});
$('overlay').addEventListener('pointerup', async () => {
  const done = op;
  op = null;
  guides = [];
  if (!done) { drawOverlay(); return; }
  if (done.type === 'move' && done.started) {
    const cell = dropCell;
    dropZone = dropCell = null;
    if (cell) setCell(done.id, cell);
    changed(true);
  }
  else if (done.type === 'area' && done.moved) changed(true);
  else if (done.type === 'resize' && !done.current && done.before) { user = JSON.parse(done.before); schedule(); }
  else if (done.type === 'resize' && done.current) {
    if (done.free) { changed(true); return; }
    const answer = await ask(t('ask-resize'), t('ask-resize-sub'), [['all', t('yes')], ['one', t('no')], ['cancel', t('cancel')]]);
    ghost = null;
    if (answer === 'all') {
      ensureStyled(screen);
      const info = menuInfo(screen);
      const m = metrics(info.menu, info.listed);
      const own = userMenu(screen, true);
      const [W] = previewSize();
      const rect = done.current;
      setPath(own, ['button_size', 'height'], pxToFile(rect[3], 'y'));
      if (m.columns === 1) {
        // Une colonne : la zone prend la largeur et la place du bouton
        setPath(own, ['area', 'x'], pxToFile(rect[0], 'x'));
        setPath(own, ['area', 'width'], pxToFile(rect[2], 'x'));
        setPath(own, ['button_size', 'width'], 1);
      } else if (rect[2] > m.columnW) {
        // Plus large que sa colonne : la zone s'elargit autour de son centre
        const width = Math.min(W, rect[2] * m.columns + (m.columns - 1) * m.gapX);
        const left = clamp(m.area[0] + m.area[2] / 2 - width / 2, 0, W - width);
        setPath(own, ['area', 'x'], pxToFile(left, 'x'));
        setPath(own, ['area', 'width'], pxToFile(width, 'x'));
        setPath(own, ['button_size', 'width'], Math.min(1, Math.round(rect[2] / ((width - (m.columns - 1) * m.gapX) / m.columns) * 1000) / 1000));
      } else setPath(own, ['button_size', 'width'], Math.round(rect[2] / m.columnW * 1000) / 1000);
      changed(true);
    } else if (answer === 'one') {
      // Lui seul : des cases entieres de la disposition, les autres se rangent autour
      ensureStyled(screen);
      const [c, r] = cellsFor(done.current);
      editButton(done.id, b => { if (c === 1 && r === 1) delete b.span; else b.span = Object.assign({}, c > 1 ? { columns: c } : {}, r > 1 ? { rows: r } : {}); });
      changed(true);
    } else {
      user = JSON.parse(done.before);
      schedule();
    }
  }
});
$('overlay').addEventListener('pointerleave', () => { if (hover) { hover = null; drawOverlay(); } });
$('overlay').addEventListener('keydown', (event) => {
  const id = currentId();
  if (event.key === 'Escape') { selectScreen(); event.preventDefault(); return; }
  const moves = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  if (!moves[event.key]) return;
  event.preventDefault();
  const geo = lastDraw && lastDraw.geometry;
  if (id && isFree(id) && geo && geo.rects[id]) {
    // Bouton place librement : les fleches le deplacent (Maj : 10 fois plus)
    const step = event.shiftKey ? 10 : 1;
    const [dx, dy] = moves[event.key];
    const r = geo.rects[id];
    setPlace(id, [r[0] + dx * step, r[1] + dy * step, r[2], r[3]]);
    changed(true);
    return;
  }
  // Sinon : d'un bouton a l'autre, comme sur la borne
  const ids = shownIds();
  if (!ids.length) return;
  const index = Math.max(0, ids.indexOf(id));
  const next = ['ArrowDown', 'ArrowRight'].includes(event.key) ? (index + 1) % ids.length : (index - 1 + ids.length) % ids.length;
  if (GAME_SCREENS.includes(screen)) { selected = next + 1; schedule(); } else selectButton(ids[next]);
});
window.addEventListener('resize', () => drawOverlay());
function ask(text, sub, choices) {
  // Question a choix dans la page (Oui / Non / Annuler)
  return new Promise((resolve) => {
    const dialog = $('ask');
    $('ask-text').textContent = text;
    $('ask-sub').textContent = sub || '';
    const row = $('ask-buttons');
    row.innerHTML = '';
    choices.forEach(([value, label], i) => {
      row.appendChild(el('button', { class: i === 0 ? 'main' : 'ghost', text: label, onclick: () => { dialog.close(); resolve(value); } }));
    });
    dialog.onclose = () => resolve('cancel');
    dialog.showModal();
  });
}

// ------------------------------------------------------------------ selection
function selectButton(id) {
  selection = { kind: 'button', id: id };
  // Dessine normalement (on voit ce qu'on change), dans l'etat choisi si son groupe est ouvert
  const index = shownIds().indexOf(id);
  selected = showSelected && index >= 0 ? index + 1 : 0;
  showTab('edit');
  buildPanel(); schedule();
}
function selectScreen() {
  selection = { kind: 'screen' };
  if (!GAME_SCREENS.includes(screen)) selected = 0;
  buildPanel(); schedule();
}
function validateSelection() {
  if (selection.kind === 'button' && !buttonOf(selection.id)) selection = { kind: 'screen' };
}

// ------------------------------------------------------------------ champs des formulaires
function el(tag, attrs, children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null) node.setAttribute(key, value);
  }
  for (const child of children || []) if (child) node.appendChild(child);
  return node;
}
function remember() {
  const now = JSON.stringify(user);
  if (now !== lastState) { history.push(lastState); if (history.length > 200) history.shift(); lastState = now; }
  $('undo').disabled = !history.length;
}
function undo() {
  if (!history.length) return;
  user = JSON.parse(history.pop());
  lastState = JSON.stringify(user);
  $('undo').disabled = !history.length;
  validateSelection();
  buildAll();
}
function changed(rebuild) {
  // Un changement du fichier : l'ecran garde ses boutons sur un seul ecran, puis fichier et apercu
  cleanUser();
  if (fitOnScreen(screen)) { fitNotice = true; rebuild = true; }
  cleanUser();
  writeYaml(); remember(); schedule();
  if (rebuild) buildPanel();
}
function field(parent, labelKey, input, hintKey) {
  parent.appendChild(el('label', { text: t(labelKey) }));
  parent.appendChild(input);
  if (hintKey) parent.appendChild(el('p', { class: 'hint', text: t(hintKey) }));
  return input;
}
function cell(parent, labelText, input) {
  parent.appendChild(el('div', {}, [el('label', { text: labelText }), input]));
}
function textInput(get, set, placeholder) {
  const input = el('input', { type: 'text', placeholder: placeholder || '' });
  input.value = get() === undefined || get() === null ? '' : (L.isDict(get()) ? '' : String(get()));
  input.addEventListener('change', () => { set(input.value.trim() === '' ? undefined : input.value); changed(); });
  return input;
}
function numberInput(get, set, step, min, max, placeholder) {
  const input = el('input', { type: 'number', step: step || 'any', min: min, max: max, placeholder: placeholder });
  const value = get();
  input.value = value === undefined || value === null ? '' : value;
  input.addEventListener('change', () => {
    const v = input.value === '' ? undefined : parseFloat(input.value);
    set(isNaN(v) ? undefined : v); changed();
  });
  return input;
}
function unitInput(get, set, axis, rebuild) {
  // Une position, une taille ou une taille de texte : en % de l'ecran ou en pixels
  const input = el('input', { type: 'number', step: 'any' });
  input.value = toUnits(get(), axis);
  input.addEventListener('change', () => { set(fromUnits(input.value)); changed(rebuild); });
  return input;
}
function selectInput(options, get, set, emptyKey, rebuild) {
  const select = el('select');
  if (emptyKey !== undefined) select.appendChild(el('option', { value: '', text: emptyKey ? t(emptyKey) : '—' }));
  for (const option of options) {
    const [value, text] = Array.isArray(option) ? option : [option, option];
    select.appendChild(el('option', { value: value, text: text }));
  }
  const value = get();
  select.value = value === undefined || value === null ? '' : String(value);
  select.addEventListener('change', () => { set(select.value === '' ? undefined : select.value); changed(rebuild); });
  return select;
}
function checkInput(labelKey, get, set, rebuild) {
  const box = el('input', { type: 'checkbox' });
  box.checked = !!get();
  box.addEventListener('change', () => { set(box.checked); changed(rebuild); });
  return el('label', { class: 'inline' }, [box, el('span', { text: t(labelKey) })]);
}
function colorInput(get, set) {
  // Couleur : nom d'une couleur du theme, ou #RRGGBB(AA) ; le selecteur ecrit #RRGGBB
  const wrap = el('div', { style: 'display:flex;gap:6px;align-items:center' });
  const listId = 'theme-colors';
  if (!$(listId)) {
    const list = el('datalist', { id: listId });
    THEME_COLORS.forEach(c => list.appendChild(el('option', { value: c })));
    document.body.appendChild(list);
  }
  const text = el('input', { type: 'text', list: listId, placeholder: 'menu-buttons, #C0392B', style: 'flex:1;min-width:0;width:100%' });
  const picker = el('input', { type: 'color' });
  const refresh = () => {
    const value = get();
    text.value = value === undefined || value === null ? '' : String(value);
    const ctx = new MenusDraw.Context(document.createElement('canvas'), { width: 10, height: 10, colors: themeSetup().colors });
    const rgb = ctx.color(value, null);
    if (rgb) picker.value = '#' + rgb.slice(0, 3).map(c => ('0' + Number(c).toString(16)).slice(-2)).join('');
  };
  text.addEventListener('change', () => { set(text.value.trim() || undefined); refresh(); changed(); });
  picker.addEventListener('input', () => {
    const old = String(get() || '');
    const alpha = old.startsWith('#') && old.length === 9 ? old.slice(7) : '';
    set(picker.value.toUpperCase() + alpha); refresh(); changed();
  });
  refresh();
  wrap.appendChild(text); wrap.appendChild(picker);
  return wrap;
}
function imageInput(get, set) {
  // Image : celles du theme, du jeu et celles chargees (liste), ou un chemin
  const listId = 'image-paths';
  let list = $(listId);
  if (!list) { list = el('datalist', { id: listId }); document.body.appendChild(list); }
  list.innerHTML = '';
  const paths = new Set(Object.keys(ownImages));
  for (const owner of [themeName(), 'official']) Object.keys((DATA.images || {})[owner] || {}).forEach(p => paths.add(p));
  if (ownTheme) Object.keys(ownTheme.images).forEach(p => paths.add(p));
  [...paths].sort().forEach(p => list.appendChild(el('option', { value: p })));
  const input = textInput(get, set, 'images/...');
  input.setAttribute('list', listId);
  input.style.width = '100%';
  return input;
}
function rectInputs(parent, get, set, rebuild) {
  // x, y, largeur, hauteur : en % ou en pixels selon la resolution
  const grid = el('div', { class: 'grid4' });
  for (const [key, axis] of [['x', 'x'], ['y', 'y'], ['width', 'x'], ['height', 'y']]) {
    cell(grid, t('u-' + key) + (reference() ? ' (px)' : ' (%)'), unitInput(() => get(key), v => set(key, v), axis, rebuild));
  }
  parent.appendChild(grid);
}
function fieldset(parent, legend, open) {
  const box = el('details', { class: 'group' });
  if (open) box.open = true;
  box.appendChild(el('summary', { text: legend }));
  parent.appendChild(box);
  return box;
}
function sizeLabel() { return reference() ? t('f-size-px') : t('f-size'); }

// Titre ou sous-titre : texte, et aspect (bloc) si l'un de ses reglages est donne
function titleFields(parent, name, key) {
  const fs = fieldset(parent, t(key === 'title' ? 'f-title' : 'f-subtitle'));
  const get = () => userMenu(name)[key];
  const look = () => (L.isDict(get()) && !Object.keys(get()).every(k => R.LANGUAGES.includes(k)) ? get() : {});
  const write = (text, lookValues) => {
    const menu = userMenu(name, true);
    const hasLook = Object.keys(lookValues).some(k => k !== 'text' && !isEmpty(lookValues[k]));
    if (hasLook) {
      const block = {};
      if (text !== undefined) block.text = text;
      for (const [k, v] of Object.entries(lookValues)) if (k !== 'text' && !isEmpty(v)) block[k] = v;
      menu[key] = block;
    } else if (text !== undefined) menu[key] = text;
    else delete menu[key];
  };
  const textOf = () => (isLook(get()) ? get().text : get());
  field(fs, 'f-text', textInput(textOf, v => write(v, look())), 'f-text-hint');
  const grid = el('div', { class: 'grid2' });
  const setLook = (k) => (v) => { const l = Object.assign({}, look()); if (isEmpty(v)) delete l[k]; else l[k] = v; write(textOf(), l); };
  cell(grid, sizeLabel(), unitInput(() => look().size, setLook('size'), 'y'));
  cell(grid, t('f-font'), selectInput(Object.keys(DATA.fonts), () => look().font, setLook('font'), ''));
  cell(grid, t('f-color'), colorInput(() => look().color, setLook('color')));
  cell(grid, t('f-band'), colorInput(() => look().background, setLook('background')));
  fs.appendChild(grid);
  fs.appendChild(checkInput('f-bold', () => look().bold, setLook('bold')));
}
function backgroundFields(parent, get, set, legend, open) {
  // Fond : couleur et/ou image, et comment l'image remplit la place
  const fs = fieldset(parent, legend, open);
  const block = () => { const b = get(); return L.isDict(b) ? b : (b ? (/\.(png|jpe?g|webp)$/i.test(b) || String(b).includes('/') ? { image: b } : { color: b }) : {}); };
  const put = (k) => (v) => { const b = Object.assign({}, block()); if (isEmpty(v)) delete b[k]; else b[k] = v; set(Object.keys(b).length ? b : undefined); };
  field(fs, 'f-color', colorInput(() => block().color, put('color')));
  field(fs, 'f-image', imageInput(() => block().image, put('image')));
  const grid = el('div', { class: 'grid2' });
  cell(grid, t('f-fit'), selectInput(FITS.map(f => [f, t('fit-' + f)]), () => block().fit, put('fit'), ''));
  cell(grid, t('f-position'), selectInput(POSITIONS.map(p => [p, t('pos-' + p)]), () => block().position, put('position'), ''));
  cell(grid, t('f-opacity'), numberInput(() => block().opacity, put('opacity'), 0.05, 0, 1));
  cell(grid, t('f-slice'), numberInput(() => block().slice, put('slice'), 1, 1, 200));
  fs.appendChild(grid);
  return fs;
}

// ------------------------------------------------------------------ panneau : l'ecran
function screenLabel(name) {
  if (T.fr['screen-' + name]) return t('screen-' + name);
  return name;
}
function buttonLabelText(button) {
  let text = button.text !== undefined ? button.text : R.buttonId(button);
  if (isLook(text)) text = text.text !== undefined ? text.text : R.buttonId(button);
  if (L.isDict(text)) text = text[lang] || text.en || Object.values(text)[0] || R.buttonId(button);
  return gameText(String(text));
}
function styleNames() { return ['classic'].concat(Object.keys(merged().styles || {}).filter(s => s !== 'classic')); }
function buildPanel() {
  validateSelection();
  const panel = $('tab-edit');
  const scroll = $('side').scrollTop;
  panel.innerHTML = '';
  if (selection.kind === 'button') buildButtonPanel(panel); else buildScreenPanel(panel);
  $('side').scrollTop = scroll;
}
function buildScreenPanel(panel) {
  const name = screen;
  const own = () => userMenu(name);
  const set = (key) => (value) => { const menu = userMenu(name, true); if (isEmpty(value)) delete menu[key]; else menu[key] = value; };
  panel.appendChild(el('h2', { text: t('sel-screen', { name: screenLabel(name) }) }));
  if (GAME_SCREENS.includes(name)) panel.appendChild(el('p', { class: 'hint', text: t('game-screen-hint') }));
  else panel.appendChild(el('p', { class: 'hint', text: t('sel-screen-hint') }));
  if (fitNotice) panel.appendChild(el('div', { class: 'note warn', text: t('fit-notice') }));
  field(panel, 'f-screen-style', selectInput(styleNames(), menuStyleName, set('style'), undefined, true),
        GAME_SCREENS.includes(name) ? 'f-style-hint-game' : null);
  if (!GAME_SCREENS.includes(name)) buildLayoutFields(panel, name);
  else if (name === 'games') {
    const fs = fieldset(panel, t('f-layout-title'), true);
    field(fs, 'f-columns', numberInput(() => own().columns, set('columns'), 1, 1, 8));
    fs.appendChild(el('label', { text: t('f-area') }));
    rectInputs(fs, k => getPath(own(), ['area', k]), (k, v) => setPath(userMenu(name, true), ['area', k], v));
    fs.appendChild(el('p', { class: 'hint', text: t('area-hint') }));
  }
  titleFields(panel, name, 'title');
  titleFields(panel, name, 'subtitle');
  backgroundFields(panel, () => own().background, set('background'), t('f-menu-background'));
  if (GAME_SCREENS.includes(name)) return;
  buildShortcutFields(panel, name);
  const effective = () => ((merged().menus || {})[name]) || {};
  const fsInfo = fieldset(panel, t('f-info'));
  fsInfo.appendChild(checkInput('f-show-version', () => effective().show_version, v => set('show_version')(v || undefined)));
  for (const item of ['version', 'rpi_version', 'ips']) {
    fsInfo.appendChild(checkInput('info-' + item, () => [].concat(effective().info || []).includes(item), v => {
      const list = [].concat(effective().info || []).filter(i => i !== item);
      if (v) list.push(item);
      set('info')(list.length ? list : null);
    }));
  }
  fsInfo.appendChild(checkInput('f-remember', () => effective().remember, v => set('remember')(v ? true : null)));
  buildButtonList(panel, name);
}
function buildLayoutFields(panel, name) {
  const fs = fieldset(panel, t('f-layout-title'), true);
  const info = menuInfo(name);
  const own = () => userMenu(name);
  const m = metrics(info.menu, info.listed);
  if (!info.styled) fs.appendChild(el('p', { class: 'hint', text: t('drawing-classic') }));
  // Chaque reglage de la disposition fait passer l'ecran au dessin par la disposition
  const write = (path, value) => { ensureStyled(name); setPath(userMenu(name, true), path, value); };
  const grid = el('div', { class: 'grid2' });
  // Les valeurs en vigueur (celles du jeu tant que le fichier n'en dit rien)
  cell(grid, t('f-layout'), selectInput([['list', t('layout-list')], ['grid', t('layout-grid')], ['tiles', t('layout-tiles')]],
    () => m.kind, v => write(['layout'], v), undefined, true));
  cell(grid, t('f-align'), selectInput([['center', t('align-center')], ['top', t('align-top')]], () => info.menu.align || 'center',
    v => write(['align'], v)));
  const columns = el('input', { type: 'number', min: 1, max: 8, step: 1, value: m.columns });
  columns.addEventListener('change', () => {
    const n = Math.max(1, parseInt(columns.value, 10) || 1);
    write(['columns'], n);
    if (n > 1 && String(info.menu.layout || 'list') === 'list') write(['layout'], 'grid');
    changed(true);
  });
  const rows = el('input', { type: 'number', min: 1, max: 20, step: 1, value: m.rows });
  rows.addEventListener('change', () => {
    // Le nombre de lignes donne celui des colonnes (tous les boutons de la disposition y tiennent)
    const n = Math.max(1, parseInt(rows.value, 10) || 1);
    const cols = Math.max(1, Math.ceil(m.flowing.length / n));
    write(['columns'], cols);
    if (cols > 1 && String(info.menu.layout || 'list') === 'list') write(['layout'], 'grid');
    changed(true);
  });
  cell(grid, t('f-columns'), columns);
  cell(grid, t('f-rows'), rows);
  cell(grid, t('f-size-width'), numberInput(() => m.size.width, v => write(['button_size', 'width'], v), 0.05, 0.1, 1));
  cell(grid, t('u-height') + (reference() ? ' (px)' : ' (%)'), unitInput(() => getPath(info.menu, ['button_size', 'height']),
    v => write(['button_size', 'height'], v), 'y', true));
  fs.appendChild(grid);
  fs.appendChild(el('div', { class: 'row', style: 'margin-top:6px' }, [el('button', { class: 'tiny', text: t('fit-area'), onclick: () => {
    // Hauteur des boutons : la zone remplie par leurs lignes
    const spaces = m.flowing.reduce((sum, b) => sum + (parseFloat(b.space_before) || 0), 0);
    write(['button_size', 'height'], pxToFile(Math.max(1, (m.area[3] - (m.rows - 1) * m.gapY) / (m.rows + spaces)), 'y', true));
    changed(true);
  } })]));
  fs.appendChild(el('label', { text: t('f-gap') }));
  const gaps = el('div', { class: 'grid2' });
  for (const [key, axis] of [['x', 'x'], ['y', 'y']]) {
    cell(gaps, t('u-' + key) + (reference() ? ' (px)' : ' (%)'), unitInput(() => getPath(info.menu, ['gap', key]) !== undefined ? getPath(info.menu, ['gap', key]) : L.GAP_DEFAULT[key],
      v => write(['gap', key], v), axis));
  }
  fs.appendChild(gaps);
  fs.appendChild(el('label', { text: t('f-area') }));
  rectInputs(fs, k => getPath(own(), ['area', k]) !== undefined ? getPath(own(), ['area', k]) : ((L.LAYOUT_DEFAULTS[m.kind] || L.LAYOUT_DEFAULTS.list).area[k]),
    (k, v) => write(['area', k], v));
  fs.appendChild(el('p', { class: 'hint', text: t('area-hint') }));
  if (info.styled) {
    fs.appendChild(el('button', { class: 'tiny', text: t('layout-remove'), onclick: () => {
      if (!confirm(t('layout-remove-confirm'))) return;
      const menu = userMenu(name, true);
      for (const key of ['layout', 'area', 'columns', 'button_size', 'gap', 'align', 'overflow']) delete menu[key];
      if (menuButtons(name).some(b => b.place)) ownButtons(name).forEach(b => delete b.place);
      changed(true);
    } }));
  }
}
function buildShortcutFields(panel, name) {
  const fs = fieldset(panel, t('f-shortcuts'));
  const sc = () => userMenu(name).shortcuts || {};
  const setSc = (k) => (v) => setPath(userMenu(name, true), ['shortcuts', k], v);
  // Par defaut comme les boutons classiques du theme
  const themeShows = () => { const pict = themeSetup().colors['main-sub-menu-shortcuts']; return pict !== null && pict !== undefined; };
  fs.appendChild(checkInput('f-sc-show', () => (sc().show !== undefined ? sc().show !== false : themeShows()),
    v => setSc('show')(v === themeShows() ? undefined : v), true));
  field(fs, 'f-sc-format', textInput(() => sc().format, setSc('format'), '{key}'));
  const grid = el('div', { class: 'grid2' });
  cell(grid, t('f-position'), selectInput(['left', 'right', 'top_left', 'top_right', 'bottom_left', 'bottom_right'].map(p => [p, t('pos-' + p)]),
    () => sc().position, setSc('position'), ''));
  cell(grid, t('f-size-part'), numberInput(() => sc().size, setSc('size'), 0.05, 0.05, 1));
  cell(grid, t('sc-box'), colorInput(() => sc().background, setSc('background')));
  cell(grid, t('sc-text'), colorInput(() => sc().color, setSc('color')));
  fs.appendChild(grid);
  fs.appendChild(checkInput('sc-nobox', () => sc().background === null, v => {
    const menu = userMenu(name, true);
    if (!L.isDict(menu.shortcuts)) menu.shortcuts = {};
    if (v) menu.shortcuts.background = null; else delete menu.shortcuts.background;
    if (!Object.keys(menu.shortcuts).length) delete menu.shortcuts;
  }, true));
}
function buildButtonList(panel, name) {
  const fs = fieldset(panel, t('buttons-title'), true);
  const list = el('ul', { class: 'buttons' });
  for (const button of menuButtons(name)) {
    const id = R.buttonId(button);
    const tags = [];
    if (button.visible === false) tags.push(t('tag-hidden'));
    if (button.footer) tags.push(t('tag-footer'));
    if (button.place) tags.push(t('tag-placed'));
    if (button.shortcut) tags.push([].concat(button.shortcut).join(', '));
    list.appendChild(el('li', { onclick: () => selectButton(id) }, [
      el('span', { class: 'name', text: buttonLabelText(button) }), el('span', { class: 'tag', text: tags.join(' · ') })]));
  }
  fs.appendChild(list);
  fs.appendChild(el('div', { class: 'row' }, [
    el('button', { class: 'tiny', text: t('btn-add'), onclick: addButton }),
    el('button', { class: 'tiny', text: t('btn-reset'), onclick: resetMenu })]));
}

// ------------------------------------------------------------------ panneau : un bouton
function actionChoices() {
  const groups = [[t('g-actions'), DATA.actions.map(a => [a, gameText(actionText(a)) + ` (${a})`])]];
  const menus = screens().filter(n => !GAME_SCREENS.includes(n) && n !== 'main');
  groups.push([t('g-menus'), menus.map(n => [`menu:${n}`, screenLabel(n)])]);
  groups.push([t('g-categories'), ['classic', 'fun', 'sport', 'favorites'].map(c => [`category:${c}`, t('cat-' + c)])]);
  const games = [];
  for (const [cat, names] of Object.entries(DATA.games)) names.forEach(n => games.push([`game:${n}`, `${n.replace(/_/g, ' ')} (${t('cat-' + cat)})`]));
  groups.push([t('g-games'), games]);
  groups.push([t('g-favorites'), Array.from({ length: 9 }, (_, i) => [`favorite:fav${i + 1}`, `${t('favorite')} ${i + 1}`])]);
  return groups;
}
function actionText(action) {
  // Texte par defaut d'une action (celui des menus du jeu)
  for (const menu of Object.values(DATA.defaults.menus || {})) {
    for (const b of (menu.buttons || [])) if (b.action === action && b.text) return b.text;
  }
  return action;
}
function editButton(id, change) {
  // Un changement d'un bouton : la liste des boutons passe dans le fichier
  const buttons = ownButtons(screen);
  const button = buttons.find(b => R.buttonId(b) === id);
  if (button) change(button, buttons);
}
function labelOf(button) {
  // Le texte du bouton tel qu'ecrit dans le fichier (hors bloc d'aspect)
  return isLook(button.text) ? button.text.text : button.text;
}
function setLabel(button, value) {
  if (isLook(button.text)) { if (value === undefined) delete button.text.text; else button.text.text = value; }
  else if (value === undefined) delete button.text; else button.text = value;
}
function buildButtonPanel(panel) {
  const id = selection.id;
  const button = buttonOf(id);
  panel.appendChild(el('a', { class: 'back', text: t('back-screen'), onclick: selectScreen }));
  panel.appendChild(el('h2', { text: t('sel-button', { name: buttonLabelText(button) }) }));
  if (fitNotice) panel.appendChild(el('div', { class: 'note warn', text: t('fit-notice') }));
  const set = (key) => (value) => editButton(id, b => { if (isEmpty(value) || value === null) delete b[key]; else b[key] = value; });
  // Contenu
  const content = fieldset(panel, t('f-text'), true);
  field(content, 'f-text', textInput(() => (L.isDict(labelOf(button)) ? undefined : labelOf(button)), v => editButton(id, b => setLabel(b, v)),
    gameText(actionText(button.action))), 'f-button-text-hint');
  const select = el('select');
  for (const [group, options] of actionChoices()) {
    const og = el('optgroup', { label: group });
    for (const [value, text] of options) og.appendChild(el('option', { value: value, text: text }));
    select.appendChild(og);
  }
  select.value = button.action || '';
  select.addEventListener('change', () => {
    const before = R.buttonId(button);
    set('action')(select.value);
    if (!button.id) selection.id = before === button.action ? select.value : before;
    changed(true);
  });
  field(content, 'f-action', select);
  field(content, 'f-shortcut', textInput(() => [].concat(button.shortcut || []).join(', '),
    v => set('shortcut')(v ? (v.includes(',') ? v.split(',').map(s => s.trim()).filter(Boolean) : v.trim()) : undefined)), 'f-shortcut-hint');
  field(content, 'f-icon', imageInput(() => R.buttonIcon(Object.assign({}, button, { game_logo: undefined })) || undefined,
    v => editButton(id, b => { if (L.isDict(b.icon)) { if (v) b.icon.image = v; else delete b.icon.image; } else if (v) b.icon = v; else delete b.icon; })));
  content.appendChild(checkInput('f-visible', () => button.visible !== false, v => set('visible')(v ? undefined : false), true));
  content.appendChild(checkInput('f-exhibition', () => !!button.exhibition, v => set('exhibition')(v || undefined)));
  field(content, 'f-confirm', textInput(() => button.confirm, set('confirm')), 'f-confirm-hint');
  const more = fieldset(content, t('more'));
  field(more, 'f-id', textInput(() => button.id, v => {
    editButton(id, b => { if (v) b.id = v; else delete b.id; });
    selection.id = v || button.action;
  }), 'f-id-hint');
  const grid = el('div', { class: 'grid2' });
  cell(grid, t('f-space-before'), numberInput(() => button.space_before, set('space_before'), 0.5, 0, 10));
  cell(grid, t('f-footer'), selectInput([['left', t('pos-left')], ['center', t('pos-center')], ['right', t('pos-right')]], () => button.footer, set('footer'), '', true));
  more.appendChild(grid);
  field(more, 'f-logo', textInput(() => button.logo, set('logo'), 'menu_classic'), 'f-logo-hint');
  // Position, taille et ordre
  if (!isFooter(id)) {
    const fs = fieldset(panel, t('pos-title'), true);
    if (L.isDict(button.place)) {
      fs.appendChild(el('p', { class: 'hint', text: t('pos-free-hint') }));
      rectInputs(fs, k => button.place[k], (k, v) => editButton(id, b => { b.place = Object.assign({}, b.place); if (v === undefined) delete b.place[k]; else b.place[k] = v; }));
      fs.appendChild(el('label', { text: t('f-anchor') }));
      fs.appendChild(selectInput(POSITIONS.map(p => [p, t('pos-' + p)]), () => button.place.anchor,
        v => editButton(id, b => { b.place = Object.assign({}, b.place); if (v) b.place.anchor = v; else delete b.place.anchor; }), ''));
      fs.appendChild(el('div', { class: 'row', style: 'margin-top:6px' }, [el('button', { class: 'tiny', text: t('pos-back-grid'),
        onclick: () => { editButton(id, b => delete b.place); changed(true); } })]));
    } else {
      fs.appendChild(el('p', { class: 'hint', text: t('pos-grid-hint') }));
      if (L.isDict(button.cell)) {
        // Case fixe : rangee et colonne comptees depuis 1 a l'ecran, depuis 0 dans le fichier
        fs.appendChild(el('label', { text: t('cell-title') }));
        const fixed = el('div', { class: 'grid2' });
        for (const key of ['row', 'column']) {
          cell(fixed, t('cell-' + key), numberInput(() => (button.cell[key] || 0) + 1, v => editButton(id, b => {
            b.cell = Object.assign({}, b.cell, { [key]: Math.max(0, Math.round(v || 1) - 1) });
          }), 1, 1, 20));
        }
        fs.appendChild(fixed);
        fs.appendChild(el('div', { class: 'row', style: 'margin-top:6px' }, [el('button', { class: 'tiny', text: t('cell-free'),
          onclick: () => { editButton(id, b => delete b.cell); changed(true); } })]));
      }
      fs.appendChild(el('label', { text: t('f-span') }));
      const grid = el('div', { class: 'grid2' });
      const span = () => (L.isDict(button.span) ? button.span : {});
      for (const key of ['columns', 'rows']) {
        cell(grid, t('span-' + key), numberInput(() => span()[key] || 1, v => editButton(id, b => {
          const next = Object.assign({}, L.isDict(b.span) ? b.span : {});
          if (!v || v <= 1) delete next[key]; else next[key] = Math.round(v);
          if (Object.keys(next).length) b.span = next; else delete b.span;
        }), 1, 1, 8));
      }
      fs.appendChild(grid);
    }
    fs.appendChild(el('div', { class: 'row', style: 'margin-top:6px' }, [el('span', { text: t('order') }),
      el('button', { class: 'tiny', text: '▲', onclick: () => moveButton(id, -1) }),
      el('button', { class: 'tiny', text: '▼', onclick: () => moveButton(id, 1) })]));
  }
  // Aspect
  const look = fieldset(panel, t('look-title'), true);
  if (isFooter(id)) look.appendChild(el('p', { class: 'hint', text: t('look-footer') }));
  else buildLookFields(look, id);
  panel.appendChild(el('div', { class: 'row', style: 'margin-top:10px' }, [
    el('button', { class: 'tiny', text: t('btn-del'), onclick: () => deleteButton(id) })]));
}

// Aspect d'un bouton : ecrit sur ce bouton seul, ou dans le style de l'ecran (tous ses boutons)
function menuStyleName() {
  const all = merged();
  return String(R.merge(all.defaults || {}, (all.menus || {})[screen] || {}).style || 'classic');
}
function ensureMenuStyle() {
  // Le style de l'ecran, a modifier : le style classique devient un style a ce nom d'ecran
  let name = menuStyleName();
  if (!L.isDict(user.styles)) user.styles = {};
  if (name === 'classic') {
    name = screen;
    let n = 2;
    while (name === 'classic' || ((merged().styles || {})[name] && !L.isDict(user.styles[name]))) name = `${screen}${n++}`;
    // Il part de l'aspect classique (texte comme les boutons classiques du theme)
    if (!L.isDict(user.styles[name])) user.styles[name] = clone((merged().styles || {}).classic || {});
    userMenu(screen, true).style = name;
  } else if (!L.isDict(user.styles[name])) user.styles[name] = {};
  return user.styles[name];
}
function inlineHas(button, path) {
  if (path[0] === 'text') return isLook(button.text) && getPath(button.text, path.slice(1)) !== undefined;
  if (path[0] === 'icon') return L.isDict(button.icon) && getPath(button.icon, path.slice(1)) !== undefined;
  if (path[0] === 'background' && path[1] === 'color' && 'color' in button) return true;
  return getPath(button, path) !== undefined;
}
function inlineSet(button, path, value) {
  // Une propriete de style ecrite sur le bouton : texte dans text: {text: ..., size: ...},
  // icone dans icon: {image: ..., size: ...}, le reste tel quel
  const [first] = path;
  if (first === 'text' || first === 'icon') {
    const inner = first === 'text' ? 'text' : 'image';
    const current = button[first];
    const block = (first === 'text' ? isLook(current) : L.isDict(current)) ? current : (current === undefined ? {} : { [inner]: current });
    setPath(block, path.slice(1), value);
    const keys = Object.keys(block).filter(k => k !== inner);
    if (!keys.length) { if (block[inner] === undefined) delete button[first]; else button[first] = block[inner]; } else button[first] = block;
    return;
  }
  if (first === 'background' && path[1] === 'color') delete button.color;
  setPath(button, path, value);
}
function buildLookFields(parent, id) {
  const info = menuInfo(screen);
  const button = info.items.find(b => R.buttonId(b) === id) || buttonOf(id);
  const effective = () => menuInfo(screen).renderer.buttonStyle(menuInfo(screen).menu, button);
  // Interrupteur : ce bouton seul ou tous les boutons de l'ecran
  const seg = el('div', { class: 'seg' });
  for (const [value, key] of [['one', 'scope-one'], ['all', 'scope-all']]) {
    seg.appendChild(el('button', { class: scope === value ? 'active' : '', text: t(key), onclick: () => { scope = value; store('scope', value); buildPanel(); } }));
  }
  parent.appendChild(seg);
  const styleName = menuStyleName();
  if (scope === 'one') parent.appendChild(el('p', { class: 'hint', text: t('scope-hint-one') }));
  else {
    parent.appendChild(el('p', { class: 'hint', text: t('scope-hint-all', { style: styleName === 'classic' ? screen : styleName }) }));
    const others = screens().filter(n => n !== screen && styleName !== 'classic' &&
      String(R.merge(merged().defaults || {}, (merged().menus || {})[n] || {}).style || 'classic') === styleName);
    if (others.length) parent.appendChild(el('div', { class: 'note warn', text: t('scope-shared', { list: others.map(screenLabel).join(', ') }) }));
  }
  const get = (path) => () => getPath(effective(), path);
  const set = (path) => (value) => {
    if (scope === 'all') {
      setPath(ensureMenuStyle(), path, value);
      // Applique aussi aux autres : ce que les boutons de l'ecran avaient en propre s'efface
      if (menuButtons(screen).some(b => inlineHas(b, path))) ownButtons(screen).forEach(b => { if (inlineHas(b, path)) inlineSet(b, path, undefined); });
    } else {
      editButton(id, b => inlineSet(b, path, value));
    }
  };
  const sizeIn = (path) => unitInput(get(path), set(path), 'y');
  const shape = el('div', { class: 'grid2' });
  cell(shape, t('f-shape'), selectInput(SHAPES.map(s => [s, t('shape-' + s)]), get(['shape']), set(['shape']), ''));
  cell(shape, t('f-radius'), numberInput(get(['radius']), set(['radius']), 0.05, 0));
  cell(shape, t('f-border-width'), numberInput(get(['border', 'width']), set(['border', 'width']), 1, 0, 30));
  cell(shape, t('f-border-color'), colorInput(get(['border', 'color']), set(['border', 'color'])));
  parent.appendChild(shape);
  parent.appendChild(checkInput('f-shadow', get(['shadow']), v => set(['shadow'])(v || undefined)));
  backgroundFields(parent, get(['background']), set(['background']), t('f-background'), true);
  const fsText = fieldset(parent, t('f-text-look'), true);
  const gt = el('div', { class: 'grid2' });
  cell(gt, t('f-font'), selectInput(Object.keys(DATA.fonts), get(['text', 'font']), set(['text', 'font']), ''));
  const autoSize = String(get(['text', 'size'])()).toLowerCase() === 'auto';
  const sizeInput = sizeIn(['text', 'size']);
  if (autoSize) { sizeInput.disabled = true; sizeInput.placeholder = 'auto'; }
  cell(gt, sizeLabel(), sizeInput);
  cell(gt, t('f-color'), colorInput(get(['text', 'color']), set(['text', 'color'])));
  cell(gt, t('f-position'), selectInput(POSITIONS.slice(0, 5).map(p => [p, t('pos-' + p)]), get(['text', 'position']), set(['text', 'position']), ''));
  cell(gt, t('f-text-align'), selectInput([['left', t('pos-left')], ['center', t('pos-center')], ['right', t('pos-right')]], get(['text', 'align']), set(['text', 'align']), ''));
  fsText.appendChild(gt);
  fsText.appendChild(checkInput('f-text-auto', () => autoSize, v => set(['text', 'size'])(v ? 'auto' : '4.5%'), true));
  fsText.appendChild(checkInput('f-bold', get(['text', 'bold']), v => set(['text', 'bold'])(v || undefined)));
  fsText.appendChild(checkInput('f-text-shadow', get(['text', 'shadow']), v => set(['text', 'shadow'])(v || undefined)));
  const fsIcon = fieldset(parent, t('f-icon-look'));
  const gi = el('div', { class: 'grid2' });
  cell(gi, t('f-position'), selectInput(['left', 'top', 'right', 'center'].map(p => [p, t('pos-' + p)]), get(['icon', 'position']), set(['icon', 'position']), ''));
  cell(gi, t('f-size-part'), numberInput(get(['icon', 'size']), set(['icon', 'size']), 0.05, 0.1, 1));
  fsIcon.appendChild(gi);
  for (const state of ['selected', 'disabled', 'pressed']) {
    const fs = fieldset(parent, t('state-' + state), state === 'selected' && showSelected);
    if (state === 'selected') {
      fs.addEventListener('toggle', () => {
        showSelected = fs.open;
        const index = shownIds().indexOf(id);
        selected = showSelected && index >= 0 ? index + 1 : 0;
        schedule();
      });
    }
    const gs = el('div', { class: 'grid2' });
    if (state !== 'pressed') {
      cell(gs, t('f-color'), colorInput(get([state, 'background', 'color']), set([state, 'background', 'color'])));
      cell(gs, t('f-text-color'), colorInput(get([state, 'text', 'color']), set([state, 'text', 'color'])));
    }
    if (state === 'selected') {
      cell(gs, t('f-border-color'), colorInput(get([state, 'border', 'color']), set([state, 'border', 'color'])));
      cell(gs, t('f-image'), imageInput(get([state, 'background', 'image']), set([state, 'background', 'image'])));
    }
    cell(gs, t('f-scale'), numberInput(get([state, 'scale']), set([state, 'scale']), 0.01, 0.5, 2));
    fs.appendChild(gs);
  }
}
function cellAt(point, id) {
  // La case de la zone des boutons sous ce point, pour ce bouton (ses cases prises) : rangee
  // et colonne depuis 0, et son rectangle a l'ecran
  const info = menuInfo(screen);
  const g = L.layout(info.menu, info.listed, previewSize(), reference(), 1).grid;
  const button = buttonOf(id) || {};
  const span = L.isDict(button.span) ? button.span : {};
  const wide = Math.min(Math.max(1, parseInt(span.columns || 1, 10)), g.columns), high = Math.max(1, parseInt(span.rows || 1, 10));
  const stepX = g.columnW + g.gapX, stepY = g.buttonH + g.gapY;
  const cellsW = wide * g.columnW + (wide - 1) * g.gapX, cellsH = high * g.buttonH + (high - 1) * g.gapY;
  const column = clamp(Math.round((point[0] - g.areaX - cellsW / 2) / stepX), 0, g.columns - wide);
  // Haut d'une rangee : celui de la grille affichee, sinon a la suite (ou depuis le haut de la zone)
  const known = Object.keys(g.tops).map(Number).sort((a, b) => a - b);
  const top = (row) => {
    if (row in g.tops) return g.tops[row];
    const last = known.filter(r => r < row).pop();
    return last !== undefined ? g.tops[last] + (row - last) * stepY : g.areaY + row * stepY;
  };
  let row = 0, best = Infinity;
  const limit = (known.length ? known[known.length - 1] : 0) + 4;
  for (let r = 0; r <= limit; r++) {
    const d = Math.abs(top(r) + cellsH / 2 - point[1]);
    if (d < best) { best = d; row = r; }
  }
  return { row: row, column: column, rect: [g.areaX + column * stepX, top(row), cellsW, cellsH] };
}
function setCell(id, cell) {
  // Le bouton fixe sur cette case de la disposition ; celui qui l'avait se range avec les autres
  for (const b of ownButtons(screen)) {
    if (R.buttonId(b) === id) { delete b.place; b.cell = { row: cell.row, column: cell.column }; }
    else if (L.isDict(b.cell) && b.cell.row === cell.row && b.cell.column === cell.column) delete b.cell;
  }
}
function snap(rect, mode, exclude, off, area) {
  // Aimante le rectangle (deplace : bords et centre ; redimensionne : le bord tire) sur le
  // centre de l'ecran, les bords et centres des autres boutons et de la zone ; garde les
  // reperes a montrer. Alt : sans aimant
  guides = [];
  if (off || !lastDraw || !lastDraw.geometry) return rect;
  const [W, H] = previewSize();
  const geo = lastDraw.geometry;
  const reach = 8 * overlayScale();
  const targets = { x: [[W / 2, true]], y: [[H / 2, true]] };
  const add = (r) => {
    targets.x.push([r[0], false], [r[0] + r[2] / 2, false], [r[0] + r[2], false]);
    targets.y.push([r[1], false], [r[1] + r[3] / 2, false], [r[1] + r[3], false]);
  };
  for (const [id, r] of Object.entries(geo.rects)) if (!exclude.includes(id)) add(r);
  if (geo.area && !area) add(geo.area);
  const result = rect.slice();
  for (const axis of ['x', 'y']) {
    const [p, size] = axis === 'x' ? [0, 2] : [1, 3];
    const low = axis === 'x' ? 'w' : 'n', high = axis === 'x' ? 'e' : 's';
    // Les bords concernes : tous en deplacement, celui de la poignee sinon
    const edges = mode === 'move' ? [[0, 'move'], [0.5, 'move'], [1, 'move']] :
      [].concat(mode.includes(low) ? [[0, 'start']] : [], mode.includes(high) ? [[1, 'end']] : []);
    let best = null;
    for (const [part, how] of edges) {
      const value = rect[p] + rect[size] * part;
      for (const [pos] of targets[axis]) {
        const d = pos - value;
        if (Math.abs(d) <= reach && (!best || Math.abs(d) < Math.abs(best.d))) best = { d: d, how: how };
      }
    }
    if (!best) continue;
    if (best.how === 'move') result[p] = Math.round(rect[p] + best.d);
    else if (best.how === 'start') { result[p] = Math.round(rect[p] + best.d); result[size] = Math.round(rect[size] - best.d); }
    else result[size] = Math.round(rect[size] + best.d);
    // Les reperes : chaque bord ou centre du rectangle aimante qui tombe sur une cible
    for (const part of [0, 0.5, 1]) {
      const value = result[p] + result[size] * part;
      for (const [pos, center] of targets[axis]) {
        if (Math.abs(pos - value) < 1 && !guides.some(gd => gd.axis === axis && Math.abs(gd.pos - pos) < 1)) guides.push({ axis: axis, pos: pos, center: center });
      }
    }
  }
  return result;
}
function addButton() {
  const buttons = ownButtons(screen);
  let n = 1;
  while (buttons.some(b => R.buttonId(b) === `button${n}`)) n++;
  const button = { id: `button${n}`, action: 'local_game', text: t('new-button') };
  const footer = buttons.findIndex(b => b.footer);
  buttons.splice(footer >= 0 ? footer : buttons.length, 0, button);
  selection = { kind: 'button', id: button.id };
  changed(true);
}
function moveButton(id, delta) {
  const buttons = ownButtons(screen);
  const index = buttons.findIndex(b => R.buttonId(b) === id);
  const target = index + delta;
  if (index < 0 || target < 0 || target >= buttons.length) return;
  [buttons[index], buttons[target]] = [buttons[target], buttons[index]];
  changed(true);
}
function deleteButton(id) {
  const buttons = ownButtons(screen);
  const index = buttons.findIndex(b => R.buttonId(b) === id);
  if (index < 0) return;
  buttons.splice(index, 1);
  selection = { kind: 'screen' };
  changed(true);
}
function resetMenu() {
  if (!confirm(t('reset-confirm'))) return;
  if (L.isDict(user.menus)) delete user.menus[screen];
  selection = { kind: 'screen' };
  fitNotice = false;
  changed(true);
}

// ------------------------------------------------------------------ images et theme de l'utilisateur
function buildImages() {
  const list = $('images');
  list.innerHTML = '';
  for (const path of Object.keys(ownImages).sort()) {
    const li = el('li', {}, [el('span', { class: 'name', text: path }),
      el('button', { class: 'tiny', text: '✕', onclick: () => { delete ownImages[path]; buildImages(); schedule(); } })]);
    list.appendChild(li);
  }
}
function loadImages(files) {
  for (const file of files) {
    const path = `images/menus/${file.name.replace(/[^A-Za-z0-9_.-]/g, '_')}`;
    ownImages[path] = URL.createObjectURL(file);
  }
  buildImages(); buildPanel(); schedule();
}
function parseColorset(text) {
  // Colorset.cfg d'un theme : section [Colorset], valeurs (r, g, b), 'texte', nombres
  const colors = {};
  let font = null;
  for (let line of text.split(/\r?\n/)) {
    line = line.replace(/#.*$/, '').trim();
    const match = line.match(/^([A-Za-z0-9_-]+)\s*[:=]\s*(.+)$/);
    if (!match) continue;
    const [, key, raw] = match;
    const value = raw.trim();
    let parsed;
    const tuple = value.match(/^\(([^)]*)\)$/);
    if (tuple) parsed = tuple[1].split(',').map(v => parseFloat(v)).filter(v => !isNaN(v));
    else if (/^['"].*['"]$/.test(value)) parsed = value.slice(1, -1);
    else if (value === 'None') parsed = null;
    else if (value === 'False') parsed = false;
    else if (value === 'True') parsed = true;
    else if (!isNaN(parseFloat(value))) parsed = parseFloat(value);
    else parsed = value;
    if (key === 'font') font = String(parsed || '').split(/[\\/]/).pop();
    else colors[key] = parsed;
  }
  return { colors: colors, font: font };
}
async function loadTheme(files) {
  const theme = { colors: {}, font: null, images: {}, fonts: {} };
  let name = '';
  for (const file of files) {
    const parts = (file.webkitRelativePath || file.name).split('/');
    name = parts[0];
    const relative = parts.slice(1).join('/');
    if (/\.(png|jpe?g|webp)$/i.test(relative) && relative.startsWith('images/')) theme.images[relative] = URL.createObjectURL(file);
    if (/\.(ttf|otf)$/i.test(relative)) theme.fonts[parts[parts.length - 1]] = URL.createObjectURL(file);
    if (/(^|\/)Colorset\.cfg$/i.test(relative)) Object.assign(theme, parseColorset(await file.text()));
  }
  ownTheme = theme;
  $('own-theme-info').textContent = t('own-theme-info', { name: name, images: Object.keys(theme.images).length,
    colors: Object.keys(theme.colors).length });
  schedule();
}

// ------------------------------------------------------------------ fichier
function writeYaml() {
  const header = `# ${t('yaml-header')}\n# docs/menu/menus.md\n`;
  const content = Object.keys(user).length ? jsyaml.dump(user, { lineWidth: 140, noRefs: true }) : '';
  $('yaml').value = header + 'version: 1\n' + content.replace(/^version: 1\n/m, '');
  store('file', JSON.stringify(user));
}
function download() {
  const blob = new Blob([$('yaml').value], { type: 'text/yaml' });
  const link = el('a', { href: URL.createObjectURL(blob), download: 'menus.yaml' });
  document.body.appendChild(link); link.click(); link.remove();
  if (Object.keys(ownImages).length) alert(t('download-images', { list: Object.keys(ownImages).join('\n') }));
}
async function openFile(file) {
  try {
    const content = jsyaml.load(await file.text());
    if (!L.isDict(content)) throw new Error(t('not-menus'));
    user = content;
    delete user.version;
    $('file-errors').textContent = '';
    remember();
    selection = { kind: 'screen' };
    buildAll();
  } catch (error) {
    $('file-errors').textContent = t('open-error') + ' ' + error.message;
  }
}

// ------------------------------------------------------------------ ecrans, resolution, premier ecran
function buildScreens() {
  const nav = $('screens');
  nav.innerHTML = '';
  for (const name of screens()) {
    const button = el('button', { class: name === screen ? 'active' : '', text: screenLabel(name) });
    button.addEventListener('click', () => {
      screen = name; selected = GAME_SCREENS.includes(name) ? 1 : 0; selection = { kind: 'screen' }; fitNotice = false; store('screen', name);
      showTab('edit'); buildAll();
    });
    nav.appendChild(button);
  }
}
function buildResolution() {
  const ref = reference();
  document.querySelectorAll('input[name="resmode"]').forEach(r => { r.checked = (r.value === (ref ? 'known' : 'auto')); });
  $('res-known-box').classList.toggle('hidden', !ref);
  const select = $('res-ref');
  select.innerHTML = '';
  RESOLUTIONS.forEach(([w, h]) => select.appendChild(el('option', { value: `${w}x${h}`, text: `${w} × ${h}` })));
  select.appendChild(el('option', { value: 'other', text: t('res-other') }));
  if (ref) {
    const key = `${ref[0]}x${ref[1]}`;
    select.value = RESOLUTIONS.some(([w, h]) => `${w}x${h}` === key) ? key : 'other';
    $('res-w').value = ref[0]; $('res-h').value = ref[1];
  }
  $('res-hint').textContent = ref ? t('res-known-hint', { w: ref[0], h: ref[1] }) : t('res-auto-hint');
  // Tailles de l'apercu : la resolution choisie, les deux de reference et les courantes
  const preview = $('preview-res');
  const keep = preview.value || stored('preview') || '1920x1080';
  preview.innerHTML = '';
  const sizes = RESOLUTIONS.slice();
  if (ref && !sizes.some(([w, h]) => w === ref[0] && h === ref[1])) sizes.unshift(ref);
  sizes.forEach(([w, h]) => preview.appendChild(el('option', { value: `${w}x${h}`, text: `${w} × ${h}` })));
  preview.value = ref ? `${ref[0]}x${ref[1]}` : ([...preview.options].some(o => o.value === keep) ? keep : '1920x1080');
}
// Les positions, tailles et tailles de texte du fichier d'une unite a l'autre : fractions de
// l'ecran (placement automatique) ou pixels d'une resolution (Units du jeu)
function convertUnits(from, to) {
  const convert = (value, axis) => {
    if (typeof value !== 'number') return value;   // '50%' : le meme partout
    const index = axis === 'x' ? 0 : 1;
    const fraction = from ? value / from[index] : value;
    return to ? Math.round(fraction * to[index]) : Math.round(fraction * 10000) / 10000;
  };
  const rect = (block) => {
    if (!L.isDict(block)) return;
    for (const key of ['x', 'width']) if (key in block) block[key] = convert(block[key], 'x');
    for (const key of ['y', 'height']) if (key in block) block[key] = convert(block[key], 'y');
  };
  const text = (block) => { if (L.isDict(block) && 'size' in block) block.size = convert(block.size, 'y'); };
  const titles = (owner) => {
    for (const key of ['title', 'subtitle']) {
      if (L.isDict(owner[key])) { text(owner[key]); rect(owner[key].place); }
    }
  };
  if (L.isDict(user.defaults)) titles(user.defaults);
  for (const menu of Object.values(user.menus || {})) {
    if (!L.isDict(menu)) continue;
    rect(menu.area); rect(menu.gap); titles(menu);
    if (L.isDict(menu.button_size) && 'height' in menu.button_size) menu.button_size.height = convert(menu.button_size.height, 'y');
    for (const button of [].concat(menu.buttons || [])) {
      if (!L.isDict(button)) continue;
      rect(button.place);
      if (isLook(button.text)) text(button.text);
    }
  }
  for (const style of Object.values(user.styles || {})) {
    if (!L.isDict(style)) continue;
    text(style.text);
    for (const state of ['selected', 'disabled', 'pressed']) if (L.isDict(style[state])) text(style[state].text);
  }
}
function setResolution(value) {
  convertUnits(reference(), value);
  if (value) user.resolution = value; else delete user.resolution;
  changed(); buildAll();
}
function buildStart() {
  const select = $('start');
  select.innerHTML = '';
  const add = (value, text) => select.appendChild(el('option', { value: value, text: text }));
  add('main', t('start-main'));
  add('local_game', t('start-local'));
  ['classic', 'fun', 'sport', 'favorites'].forEach(c => add(`category:${c}`, `${t('start-category')} : ${t('cat-' + c)}`));
  for (const names of Object.values(DATA.games)) names.forEach(n => add(`game:${n}`, `${t('start-game')} : ${n.replace(/_/g, ' ')}`));
  select.value = user.start || 'main';
}
function buildThemes() {
  const select = $('theme');
  const keep = select.value || stored('theme') || 'remi';
  select.innerHTML = '';
  [['clear', 'clear'], ['remi', 'remi'], ['own', t('theme-own')]].forEach(([v, text]) => select.appendChild(el('option', { value: v, text: text })));
  select.value = keep;
  $('own-theme').classList.toggle('hidden', select.value !== 'own');
}
function showTab(name) {
  $('tab-edit').classList.toggle('hidden', name !== 'edit');
  $('tab-file').classList.toggle('hidden', name !== 'file');
  $('tab-edit-btn').classList.toggle('active', name === 'edit');
  $('tab-file-btn').classList.toggle('active', name === 'file');
}
function buildAll() {
  writeYaml();
  buildScreens(); buildResolution(); buildStart(); buildImages(); buildPanel();
  schedule();
}
function translate() {
  document.documentElement.lang = lang;
  document.title = `RaspyDarts · ${t('menu-custom')}`;
  document.querySelectorAll('[data-t]').forEach(node => { node.innerHTML = t(node.dataset.t); });
  buildThemes();
  buildAll();
}

// ------------------------------------------------------------------ evenements
$('lang').addEventListener('change', () => { lang = $('lang').value; store('lang', lang); translate(); });
$('tab-edit-btn').addEventListener('click', () => showTab('edit'));
$('tab-file-btn').addEventListener('click', () => showTab('file'));
$('new-file').addEventListener('click', () => { if (confirm(t('new-confirm'))) { user = {}; selection = { kind: 'screen' }; remember(); buildAll(); } });
$('open-file').addEventListener('change', (e) => { if (e.target.files[0]) openFile(e.target.files[0]); e.target.value = ''; });
$('download').addEventListener('click', download);
$('download2').addEventListener('click', download);
$('undo').addEventListener('click', undo);
document.addEventListener('keydown', (event) => {
  const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes((document.activeElement || {}).tagName);
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z' && !typing) { event.preventDefault(); undo(); }
});
document.querySelectorAll('input[name="resmode"]').forEach(r => r.addEventListener('change', () => {
  if (r.value === 'auto' && r.checked) setResolution(null);
  if (r.value === 'known' && r.checked) setResolution([1920, 1080]);
}));
$('res-ref').addEventListener('change', () => {
  const v = $('res-ref').value;
  if (v !== 'other') setResolution(v.split('x').map(Number));
  else { $('res-w').focus(); }
});
['res-w', 'res-h'].forEach(id => $(id).addEventListener('change', () => {
  const w = parseInt($('res-w').value, 10), h = parseInt($('res-h').value, 10);
  if (w > 0 && h > 0) setResolution([w, h]);
}));
$('start').addEventListener('change', () => { const v = $('start').value; if (v === 'main') delete user.start; else user.start = v; changed(); });
$('theme').addEventListener('change', () => { store('theme', $('theme').value); $('own-theme').classList.toggle('hidden', $('theme').value !== 'own'); buildPanel(); schedule(); });
$('theme-folder').addEventListener('change', (e) => loadTheme([...e.target.files]));
$('preview-res').addEventListener('change', () => { store('preview', $('preview-res').value); schedule(); });
$('fav-games').addEventListener('change', () => { buildPanel(); schedule(); });
$('images-load').addEventListener('change', (e) => { loadImages([...e.target.files]); e.target.value = ''; });

// ------------------------------------------------------------------ demarrage
const browser = (navigator.language || 'fr').slice(0, 2);
lang = stored('lang') || (LANGS.includes(browser) ? browser : 'en');
$('lang').value = lang;
scope = stored('scope') === 'all' ? 'all' : 'one';
try { const saved = JSON.parse(stored('file') || '{}'); if (L.isDict(saved)) user = saved; } catch (e) { user = {}; }
lastState = JSON.stringify(user);
screen = stored('screen') || 'main';
if (!screens().includes(screen)) screen = 'main';
translate();
