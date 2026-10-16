// Configurateur du fichier de menus (docs/menu/menus.md) : formulaires, apercu, fichier menus.yaml.
// Le fichier ne contient que ce qui change par rapport aux menus du jeu (menus/defaults.yaml).
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
const THEME_COLORS = ['menu-buttons', 'menu-selected', 'menu-shortcut', 'menu-header', 'menu-text', 'menu-text-black',
  'menu-text-white', 'menu-border', 'menu-alternate', 'menu-ok', 'menu-warning', 'menu-ko', 'menu-inactive', 'menu-favorite'];

let lang = 'fr';
let user = {};               // contenu du fichier menus.yaml
let screen = 'main';         // menu montre et edite
let selected = 1;            // bouton selectionne dans l'apercu (ordre affiche)
let current = null;          // id du bouton edite
let styleName = null;        // style edite
const ownImages = {};        // images chargees : chemin -> URL locale
let ownTheme = null;         // theme charge : {colors, font, images}
let lastDraw = null;         // zones de l'apercu

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
  if (L.isDict(user.styles) && !Object.keys(user.styles).length) delete user.styles;
}
function screens() {
  const menus = Object.keys(merged().menus || {}).filter(n => !['favorite_save', 'favorite_players', 'favorite_game', 'question'].includes(n));
  const own = menus.filter(n => !FILE_MENUS.includes(n) && !GAME_SCREENS.includes(n));
  return FILE_MENUS.concat(own, GAME_SCREENS);
}

// ------------------------------------------------------------------ resolution
function reference() { return Array.isArray(user.resolution) ? user.resolution : null; }
function previewSize() {
  const value = $('preview-res').value || '1920x1080';
  return value.split('x').map(Number);
}
// Positions et tailles : en % de l'ecran (placement automatique) ou en pixels de la resolution choisie
function toUnits(value, axis) {
  if (value === undefined || value === null || value === '') return '';
  if (reference()) return Math.round(new L.Units(reference(), reference()).length(value, axis));
  const size = axis === 'x' ? 1 : 1;
  return Math.round(new L.Units([size, size], null).length(value, axis) * 10000) / 100;
}
function fromUnits(text) {
  if (text === '' || text === null) return undefined;
  const number = parseFloat(String(text).replace(',', '.'));
  if (isNaN(number)) return undefined;
  return reference() ? Math.round(number) : Math.round(number * 100) / 10000;
}

// ------------------------------------------------------------------ apercu
function themeName() { return $('theme').value || 'remi'; }
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
  const all = merged();
  const favoriteList = $('fav-games').checked ? ['Cricket', 'Low_Score'] : [];
  const renderer = new R.Renderer(DATA, all, {
    ctx: ctx, language: lang, theme: themeName(), imageUrl: imageUrl, favoriteGames: $('fav-games').checked,
    favoriteList: favoriteList, favorites: {}
  });
  try {
    if (screen === 'games') lastDraw = renderer.drawGames(selected);
    else if (screen === 'options') lastDraw = renderer.drawOptions(selected);
    else if (screen === 'players') lastDraw = renderer.drawPlayers(selected);
    else lastDraw = renderer.draw(screen, selected);
    lastDraw.renderer = renderer;
    $('file-errors').textContent = '';
  } catch (error) {
    $('file-errors').textContent = t('draw-error') + ' ' + error.message;
    console.error(error);
  }
}
// Ordre affiche des boutons (liste, puis ceux du bas) : leurs ids
function shownIds() {
  const renderer = lastDraw && lastDraw.renderer;
  if (!renderer || !FILE_MENUS.concat(screens()).includes(screen) || GAME_SCREENS.includes(screen)) return [];
  const items = renderer.items(screen);
  const listed = items.filter(b => !R.FOOTERS[b.footer]), footers = items.filter(b => R.FOOTERS[b.footer]);
  return listed.concat(footers).map(R.buttonId);
}

// ------------------------------------------------------------------ formulaires
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
function changed() { cleanUser(); writeYaml(); schedule(); }
function field(parent, labelKey, input, hintKey) {
  parent.appendChild(el('label', { text: t(labelKey) }));
  parent.appendChild(input);
  if (hintKey) parent.appendChild(el('p', { class: 'hint', text: t(hintKey) }));
  return input;
}
function textInput(get, set, placeholder) {
  const input = el('input', { type: 'text', placeholder: placeholder || '' });
  input.value = get() === undefined || get() === null ? '' : (L.isDict(get()) ? '' : String(get()));
  input.addEventListener('change', () => { set(input.value.trim() === '' ? undefined : input.value); changed(); });
  return input;
}
function numberInput(get, set, step, min, max) {
  const input = el('input', { type: 'number', step: step || 'any', min: min, max: max });
  const value = get();
  input.value = value === undefined || value === null ? '' : value;
  input.addEventListener('change', () => {
    const v = input.value === '' ? undefined : parseFloat(input.value);
    set(isNaN(v) ? undefined : v); changed();
  });
  return input;
}
function selectInput(options, get, set, emptyKey) {
  const select = el('select');
  if (emptyKey !== undefined) select.appendChild(el('option', { value: '', text: emptyKey ? t(emptyKey) : '—' }));
  for (const option of options) {
    const [value, text] = Array.isArray(option) ? option : [option, option];
    select.appendChild(el('option', { value: value, text: text }));
  }
  const value = get();
  select.value = value === undefined || value === null ? '' : String(value);
  select.addEventListener('change', () => { set(select.value === '' ? undefined : select.value); changed(); });
  return select;
}
function checkInput(labelKey, get, set) {
  const box = el('input', { type: 'checkbox' });
  box.checked = !!get();
  box.addEventListener('change', () => { set(box.checked); changed(); });
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
function unitInputs(parent, keys, get, set) {
  // x, y, largeur, hauteur : en % ou en pixels selon la resolution
  const grid = el('div', { class: 'grid4' });
  for (const [key, axis] of keys) {
    const box = el('div');
    box.appendChild(el('label', { text: t('u-' + key) + (reference() ? ' (px)' : ' (%)') }));
    const input = el('input', { type: 'number', step: 'any' });
    input.value = toUnits(get(key), axis);
    input.addEventListener('change', () => { set(key, fromUnits(input.value)); changed(); });
    box.appendChild(input);
    grid.appendChild(box);
  }
  parent.appendChild(grid);
}

// Titre ou sous-titre : texte, et aspect (bloc) si l'un de ses reglages est donne
function titleFields(parent, name, key) {
  const fs = el('fieldset', {}, [el('legend', { text: t(key === 'title' ? 'f-title' : 'f-subtitle') })]);
  const get = () => userMenu(name)[key];
  const look = () => (L.isDict(get()) ? get() : {});
  const write = (text, lookValues) => {
    const menu = userMenu(name, true);
    const hasLook = Object.keys(lookValues).some(k => !isEmpty(lookValues[k]));
    if (hasLook) {
      const block = {};
      if (text !== undefined) block.text = text;
      for (const [k, v] of Object.entries(lookValues)) if (!isEmpty(v)) block[k] = v;
      menu[key] = block;
    } else if (text !== undefined) menu[key] = text;
    else delete menu[key];
  };
  const textOf = () => (L.isDict(get()) ? get().text : get());
  field(fs, 'f-text', textInput(textOf, v => write(v, look())), 'f-text-hint');
  const grid = el('div', { class: 'grid2' });
  const sub = (k, input) => { const box = el('div'); box.appendChild(el('label', { text: t('f-' + k) })); box.appendChild(input); grid.appendChild(box); };
  const setLook = (k) => (v) => { const l = Object.assign({}, look()); if (isEmpty(v)) delete l[k]; else l[k] = v; write(textOf(), l); };
  grid.appendChild(el('div', {}, [el('label', { text: sizeLabel() }), numberInput(() => look().size, setLook('size'), reference() ? 1 : 0.005, 0)]));
  sub('font', selectInput(Object.keys(DATA.fonts), () => look().font, setLook('font'), ''));
  sub('color', colorInput(() => look().color, setLook('color')));
  sub('band', colorInput(() => look().background, setLook('background')));
  fs.appendChild(grid);
  fs.appendChild(checkInput('f-bold', () => look().bold, setLook('bold')));
  parent.appendChild(fs);
}
function backgroundFields(parent, get, set, legendKey) {
  // Fond : couleur et/ou image, et comment l'image remplit la place
  const fs = el('fieldset', {}, [el('legend', { text: t(legendKey || 'f-background') })]);
  const block = () => { const b = get(); return L.isDict(b) ? b : (b ? (/\.(png|jpe?g|webp)$/i.test(b) || String(b).includes('/') ? { image: b } : { color: b }) : {}); };
  const put = (k) => (v) => { const b = Object.assign({}, block()); if (isEmpty(v)) delete b[k]; else b[k] = v; set(Object.keys(b).length ? b : undefined); };
  field(fs, 'f-color', colorInput(() => block().color, put('color')));
  field(fs, 'f-image', imageInput(() => block().image, put('image')));
  const grid = el('div', { class: 'grid2' });
  const sub = (k, input) => { const box = el('div'); box.appendChild(el('label', { text: t('f-' + k) })); box.appendChild(input); grid.appendChild(box); };
  sub('fit', selectInput(FITS.map(f => [f, t('fit-' + f)]), () => block().fit, put('fit'), ''));
  sub('position', selectInput(POSITIONS.map(p => [p, t('pos-' + p)]), () => block().position, put('position'), ''));
  sub('opacity', numberInput(() => block().opacity, put('opacity'), 0.05, 0, 1));
  sub('slice', numberInput(() => block().slice, put('slice'), 1, 1, 200));
  fs.appendChild(grid);
  parent.appendChild(fs);
}

function buildMenuForm() {
  const form = $('menu-form');
  form.innerHTML = '';
  $('menu-name').textContent = screenLabel(screen);
  const name = screen;
  const own = () => userMenu(name);
  const set = (key) => (value) => { const menu = userMenu(name, true); if (isEmpty(value)) delete menu[key]; else menu[key] = value; };
  const effective = () => ((merged().menus || {})[name]) || {};
  titleFields(form, name, 'title');
  titleFields(form, name, 'subtitle');
  backgroundFields(form, () => own().background, set('background'), 'f-menu-background');
  const styles = ['classic'].concat(Object.keys(merged().styles || {}).filter(s => s !== 'classic'));
  field(form, 'f-style', selectInput(styles, () => own().style, set('style'), ''), GAME_SCREENS.includes(name) ? 'f-style-hint-game' : 'f-style-hint');
  if (!GAME_SCREENS.includes(name) || name === 'games') {
    const fs = el('fieldset', {}, [el('legend', { text: t('f-layout-title') })]);
    if (name !== 'games') {
      field(fs, 'f-layout', selectInput([['list', t('layout-list')], ['grid', t('layout-grid')], ['tiles', t('layout-tiles')]],
        () => own().layout, set('layout'), ''));
    }
    field(fs, 'f-columns', numberInput(() => own().columns, set('columns'), 1, 1, 8));
    if (name !== 'games') {
      field(fs, 'f-overflow', selectInput([['pages', t('overflow-pages')], ['scroll', t('overflow-scroll')]], () => own().overflow, set('overflow'), ''));
      field(fs, 'f-align', selectInput([['center', t('align-center')], ['top', t('align-top')]], () => own().align, set('align'), ''));
    }
    fs.appendChild(el('label', { text: t('f-area') }));
    unitInputs(fs, [['x', 'x'], ['y', 'y'], ['width', 'x'], ['height', 'y']], k => getPath(own(), ['area', k]),
      (k, v) => setPath(userMenu(name, true), ['area', k], v));
    if (name !== 'games') {
      fs.appendChild(el('label', { text: t('f-button-size') }));
      const grid = el('div', { class: 'grid2' });
      const box1 = el('div', {}, [el('label', { text: t('f-size-width') })]);
      box1.appendChild(numberInput(() => getPath(own(), ['button_size', 'width']), v => setPath(userMenu(name, true), ['button_size', 'width'], v), 0.05, 0.1, 1));
      const box2 = el('div', {}, [el('label', { text: t('u-height') + (reference() ? ' (px)' : ' (%)') })]);
      const h = el('input', { type: 'number', step: 'any' });
      h.value = toUnits(getPath(own(), ['button_size', 'height']), 'y');
      h.addEventListener('change', () => { setPath(userMenu(name, true), ['button_size', 'height'], fromUnits(h.value)); changed(); });
      box2.appendChild(h);
      grid.appendChild(box1); grid.appendChild(box2);
      fs.appendChild(grid);
    }
    fs.appendChild(el('label', { text: t('f-gap') }));
    unitInputs(fs, [['x', 'x'], ['y', 'y']], k => getPath(own(), ['gap', k]), (k, v) => setPath(userMenu(name, true), ['gap', k], v));
    form.appendChild(fs);
  }
  if (!GAME_SCREENS.includes(name)) {
    const fs = el('fieldset', {}, [el('legend', { text: t('f-shortcuts') })]);
    const sc = () => own().shortcuts || {};
    const setSc = (k) => (v) => setPath(userMenu(name, true), ['shortcuts', k], v);
    fs.appendChild(checkInput('f-sc-hide', () => sc().show === false, v => setSc('show')(v ? false : undefined)));
    field(fs, 'f-sc-format', textInput(() => sc().format, setSc('format'), '{key}'));
    field(fs, 'f-color', colorInput(() => sc().color, setSc('color')));
    const grid = el('div', { class: 'grid2' });
    grid.appendChild(el('div', {}, [el('label', { text: t('f-position') }),
      selectInput(['left', 'right', 'top_left', 'top_right', 'bottom_left', 'bottom_right'].map(p => [p, t('pos-' + p)]), () => sc().position, setSc('position'), '')]));
    grid.appendChild(el('div', {}, [el('label', { text: t('f-size-part') }), numberInput(() => sc().size, setSc('size'), 0.05, 0.05, 1)]));
    fs.appendChild(grid);
    form.appendChild(fs);
    const fsInfo = el('fieldset', {}, [el('legend', { text: t('f-info') })]);
    fsInfo.appendChild(checkInput('f-show-version', () => effective().show_version, v => set('show_version')(v || undefined)));
    for (const item of ['version', 'rpi_version', 'ips']) {
      fsInfo.appendChild(checkInput('info-' + item, () => (R.merge ? [].concat(effective().info || []) : []).includes(item), v => {
        const list = [].concat(effective().info || []).filter(i => i !== item);
        if (v) list.push(item);
        set('info')(list.length ? list : null);
      }));
    }
    fsInfo.appendChild(checkInput('f-remember', () => effective().remember, v => set('remember')(v ? true : null)));
    form.appendChild(fsInfo);
  }
}

// ------------------------------------------------------------------ boutons
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
function buttonLabelText(button) {
  let text = button.text !== undefined ? button.text : R.buttonId(button);
  if (L.isDict(text)) text = text[lang] || text.en || Object.values(text)[0] || R.buttonId(button);
  return gameText(String(text));
}
function buildButtons() {
  const name = screen;
  const panel = $('buttons-panel');
  if (GAME_SCREENS.includes(name)) { panel.classList.add('hidden'); return; }
  panel.classList.remove('hidden');
  const list = $('buttons');
  list.innerHTML = '';
  const buttons = menuButtons(name);
  if (!current || !buttons.some(b => R.buttonId(b) === current)) current = buttons.length ? R.buttonId(buttons[0]) : null;
  for (const button of buttons) {
    const id = R.buttonId(button);
    const tags = [];
    if (button.visible === false) tags.push(t('tag-hidden'));
    if (button.footer) tags.push(t('tag-footer'));
    if (button.place) tags.push(t('tag-placed'));
    if (button.shortcut) tags.push([].concat(button.shortcut).join(', '));
    const li = el('li', { class: id === current ? 'active' : '' }, [
      el('span', { class: 'name', text: buttonLabelText(button) }), el('span', { class: 'tag', text: tags.join(' · ') })]);
    li.addEventListener('click', () => {
      current = id;
      const index = shownIds().indexOf(id);
      if (index >= 0) selected = index + 1;
      buildButtons(); schedule();
    });
    list.appendChild(li);
  }
  buildButtonForm();
}
function editButton(change) {
  // Un changement du bouton edite : la liste des boutons passe dans le fichier
  const buttons = ownButtons(screen);
  const button = buttons.find(b => R.buttonId(b) === current);
  if (button) change(button, buttons);
}
function buildButtonForm() {
  const form = $('button-form');
  form.innerHTML = '';
  const button = menuButtons(screen).find(b => R.buttonId(b) === current);
  if (!button) return;
  const get = (key) => () => button[key];
  const set = (key) => (value) => editButton(b => { if (isEmpty(value) || value === null) delete b[key]; else b[key] = value; });
  // Action
  const select = el('select');
  for (const [group, options] of actionChoices()) {
    const og = el('optgroup', { label: group });
    for (const [value, text] of options) og.appendChild(el('option', { value: value, text: text }));
    select.appendChild(og);
  }
  select.value = button.action || '';
  select.addEventListener('change', () => { set('action')(select.value); changed(); buildButtons(); });
  field(form, 'f-action', select);
  field(form, 'f-id', textInput(get('id'), v => {
    editButton(b => { if (v) b.id = v; else delete b.id; });
    current = v || button.action;
  }), 'f-id-hint');
  field(form, 'f-text', textInput(() => (L.isDict(button.text) ? undefined : button.text), set('text'), gameText(actionText(button.action))), 'f-button-text-hint');
  field(form, 'f-shortcut', textInput(() => [].concat(button.shortcut || []).join(', '),
    v => set('shortcut')(v ? (v.includes(',') ? v.split(',').map(s => s.trim()).filter(Boolean) : v.trim()) : undefined)), 'f-shortcut-hint');
  form.appendChild(checkInput('f-visible', () => button.visible !== false, v => set('visible')(v ? undefined : false)));
  form.appendChild(checkInput('f-exhibition', () => !!button.exhibition, v => set('exhibition')(v || undefined)));
  field(form, 'f-confirm', textInput(get('confirm'), set('confirm')), 'f-confirm-hint');
  const grid = el('div', { class: 'grid2' });
  grid.appendChild(el('div', {}, [el('label', { text: t('f-space-before') }), numberInput(get('space_before'), set('space_before'), 0.5, 0, 10)]));
  grid.appendChild(el('div', {}, [el('label', { text: t('f-footer') }),
    selectInput([['left', t('pos-left')], ['center', t('pos-center')], ['right', t('pos-right')]], get('footer'), set('footer'), '')]));
  form.appendChild(grid);
  field(form, 'f-logo', textInput(get('logo'), set('logo'), 'menu_classic'), 'f-logo-hint');
  field(form, 'f-icon', imageInput(() => (typeof button.icon === 'string' ? button.icon : undefined), set('icon')));
  // Placement libre
  const fs = el('fieldset', {}, [el('legend', { text: t('f-place') })]);
  fs.appendChild(checkInput('f-place-on', () => L.isDict(button.place), v => {
    editButton(b => {
      if (!v) { delete b.place; return; }
      const zone = lastDraw && lastDraw.zones && lastDraw.zones[shownIds().indexOf(current) + 1];
      const [W, H] = previewSize();
      const conv = (px, axis) => reference() ? Math.round(px * (axis === 'x' ? reference()[0] / W : reference()[1] / H))
        : Math.round(px / (axis === 'x' ? W : H) * 10000) / 10000;
      b.place = zone ? { x: conv(zone[0], 'x'), y: conv(zone[1], 'y'), width: conv(zone[2], 'x'), height: conv(zone[3], 'y') }
        : { x: conv(W * 0.4, 'x'), y: conv(H * 0.4, 'y'), width: conv(W * 0.2, 'x'), height: conv(H * 0.09, 'y') };
    });
    buildButtons();
  }));
  if (L.isDict(button.place)) {
    unitInputs(fs, [['x', 'x'], ['y', 'y'], ['width', 'x'], ['height', 'y']], k => button.place[k],
      (k, v) => editButton(b => { b.place = Object.assign({}, b.place); if (v === undefined) delete b.place[k]; else b.place[k] = v; }));
    fs.appendChild(el('label', { text: t('f-anchor') }));
    fs.appendChild(selectInput(POSITIONS.map(p => [p, t('pos-' + p)]), () => button.place.anchor,
      v => editButton(b => { b.place = Object.assign({}, b.place); if (v) b.place.anchor = v; else delete b.place.anchor; }), ''));
    fs.appendChild(el('p', { class: 'hint', text: t('f-place-hint') }));
  }
  form.appendChild(fs);
  // Aspect de ce bouton seul
  const fsLook = el('fieldset', {}, [el('legend', { text: t('f-button-look') })]);
  const styles = ['classic'].concat(Object.keys(merged().styles || {}).filter(s => s !== 'classic'));
  field(fsLook, 'f-style', selectInput(styles, get('style'), set('style'), ''));
  field(fsLook, 'f-color', colorInput(get('color'), set('color')), 'f-button-color-hint');
  fsLook.appendChild(el('label', { text: t('f-shape') }));
  fsLook.appendChild(selectInput([['rounded', t('shape-rounded')], ['rectangle', t('shape-rectangle')], ['pill', t('shape-pill')], ['none', t('shape-none')]],
    get('shape'), set('shape'), ''));
  form.appendChild(fsLook);
}
function addButton() {
  const buttons = ownButtons(screen);
  let n = 1;
  while (buttons.some(b => R.buttonId(b) === `button${n}`)) n++;
  const button = { id: `button${n}`, action: 'local_game', text: t('new-button') };
  const footer = buttons.findIndex(b => b.footer);
  buttons.splice(footer >= 0 ? footer : buttons.length, 0, button);
  current = button.id;
  changed(); buildButtons();
}
function moveButton(delta) {
  const buttons = ownButtons(screen);
  const index = buttons.findIndex(b => R.buttonId(b) === current);
  const target = index + delta;
  if (index < 0 || target < 0 || target >= buttons.length) return;
  [buttons[index], buttons[target]] = [buttons[target], buttons[index]];
  changed(); buildButtons();
}
function deleteButton() {
  const buttons = ownButtons(screen);
  const index = buttons.findIndex(b => R.buttonId(b) === current);
  if (index < 0) return;
  buttons.splice(index, 1);
  current = null;
  changed(); buildButtons();
}
function resetMenu() {
  if (!confirm(t('reset-confirm'))) return;
  if (L.isDict(user.menus)) delete user.menus[screen];
  current = null;
  changed(); buildAll();
}

// ------------------------------------------------------------------ styles
function buildStyles() {
  const select = $('style-name');
  const names = Object.keys(user.styles || {});
  select.innerHTML = '';
  names.forEach(n => select.appendChild(el('option', { value: n, text: n })));
  if (!names.includes(styleName)) styleName = names[0] || null;
  if (styleName) select.value = styleName;
  $('style-del').disabled = !styleName;
  const form = $('style-form');
  form.innerHTML = '';
  if (!styleName) { form.appendChild(el('p', { class: 'hint', text: t('styles-none') })); return; }
  const style = () => user.styles[styleName];
  const set = (path) => (value) => setPath(user.styles[styleName] || (user.styles[styleName] = {}), path, value);
  const get = (path) => () => getPath(style(), path);
  const grid = el('div', { class: 'grid2' });
  const sub = (labelKey, input) => grid.appendChild(el('div', {}, [el('label', { text: t(labelKey) }), input]));
  sub('f-shape', selectInput([['rounded', t('shape-rounded')], ['rectangle', t('shape-rectangle')], ['pill', t('shape-pill')], ['none', t('shape-none')]], get(['shape']), set(['shape']), ''));
  sub('f-radius', numberInput(get(['radius']), set(['radius']), 0.01, 0));
  sub('f-border-width', numberInput(get(['border', 'width']), set(['border', 'width']), 1, 0, 30));
  sub('f-border-color', colorInput(get(['border', 'color']), set(['border', 'color'])));
  form.appendChild(grid);
  form.appendChild(checkInput('f-shadow', get(['shadow']), v => set(['shadow'])(v || undefined)));
  backgroundFields(form, get(['background']), set(['background']), 'f-background');
  const fsText = el('fieldset', {}, [el('legend', { text: t('f-text-look') })]);
  const gt = el('div', { class: 'grid2' });
  const subt = (labelKey, input) => gt.appendChild(el('div', {}, [el('label', { text: t(labelKey) }), input]));
  subt('f-font', selectInput(Object.keys(DATA.fonts), get(['text', 'font']), set(['text', 'font']), ''));
  gt.appendChild(el('div', {}, [el('label', { text: sizeLabel() }), numberInput(get(['text', 'size']), set(['text', 'size']), reference() ? 1 : 0.005, 0)]));
  subt('f-color', colorInput(get(['text', 'color']), set(['text', 'color'])));
  subt('f-position', selectInput(POSITIONS.slice(0, 5).map(p => [p, t('pos-' + p)]), get(['text', 'position']), set(['text', 'position']), ''));
  subt('f-text-align', selectInput([['left', t('pos-left')], ['center', t('pos-center')], ['right', t('pos-right')]], get(['text', 'align']), set(['text', 'align']), ''));
  fsText.appendChild(gt);
  fsText.appendChild(checkInput('f-bold', get(['text', 'bold']), v => set(['text', 'bold'])(v || undefined)));
  fsText.appendChild(checkInput('f-text-shadow', get(['text', 'shadow']), v => set(['text', 'shadow'])(v || undefined)));
  form.appendChild(fsText);
  const fsIcon = el('fieldset', {}, [el('legend', { text: t('f-icon-look') })]);
  const gi = el('div', { class: 'grid2' });
  gi.appendChild(el('div', {}, [el('label', { text: t('f-position') }), selectInput(['left', 'top', 'right', 'center'].map(p => [p, t('pos-' + p)]), get(['icon', 'position']), set(['icon', 'position']), '')]));
  gi.appendChild(el('div', {}, [el('label', { text: t('f-size-part') }), numberInput(get(['icon', 'size']), set(['icon', 'size']), 0.05, 0.1, 1)]));
  fsIcon.appendChild(gi);
  form.appendChild(fsIcon);
  for (const state of ['selected', 'disabled', 'pressed']) {
    const fs = el('fieldset', {}, [el('legend', { text: t('state-' + state) })]);
    const gs = el('div', { class: 'grid2' });
    const subs = (labelKey, input) => gs.appendChild(el('div', {}, [el('label', { text: t(labelKey) }), input]));
    if (state !== 'pressed') {
      subs('f-color', colorInput(get([state, 'background', 'color']), set([state, 'background', 'color'])));
      subs('f-text-color', colorInput(get([state, 'text', 'color']), set([state, 'text', 'color'])));
    }
    if (state === 'selected') {
      subs('f-border-color', colorInput(get([state, 'border', 'color']), set([state, 'border', 'color'])));
      subs('f-image', imageInput(get([state, 'background', 'image']), set([state, 'background', 'image'])));
    }
    subs('f-scale', numberInput(get([state, 'scale']), set([state, 'scale']), 0.01, 0.5, 2));
    fs.appendChild(gs);
    form.appendChild(fs);
  }
}
function addStyle() {
  const name = ($('style-new').value || '').trim().replace(/[^A-Za-z0-9_-]/g, '_');
  if (!name || name === 'classic') { $('style-new').focus(); return; }
  $('style-new').value = '';
  if (!L.isDict(user.styles)) user.styles = {};
  if (!user.styles[name]) user.styles[name] = { shape: 'rounded', background: { color: 'menu-buttons' }, selected: { background: { color: 'menu-selected' } } };
  styleName = name;
  changed(); buildStyles(); buildMenuForm(); buildButtonForm();
}
function deleteStyle() {
  if (!styleName || !confirm(t('style-del-confirm', { name: styleName }))) return;
  delete user.styles[styleName];
  styleName = null;
  changed(); buildStyles(); buildMenuForm(); buildButtonForm();
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
  buildImages(); buildButtonForm(); schedule();
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
    buildAll();
  } catch (error) {
    $('file-errors').textContent = t('open-error') + ' ' + error.message;
  }
}

// ------------------------------------------------------------------ ecran, resolution, premier ecran
function screenLabel(name) {
  if (T.fr['screen-' + name]) return t('screen-' + name);
  return name;
}
function buildScreens() {
  const nav = $('screens');
  nav.innerHTML = '';
  for (const name of screens()) {
    const button = el('button', { class: name === screen ? 'active' : '', text: screenLabel(name) });
    button.addEventListener('click', () => { screen = name; selected = 1; current = null; store('screen', name); buildAll(); });
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
      if (L.isDict(button.text) && !Object.keys(button.text).every(k => R.LANGUAGES.includes(k))) text(button.text);
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
// Taille d'un texte : part de la hauteur de l'ecran, ou pixels de la resolution choisie
function sizeLabel() { return reference() ? t('f-size-px') : t('f-size'); }
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
function buildAll() {
  writeYaml();
  buildScreens(); buildResolution(); buildStart(); buildMenuForm(); buildButtons(); buildStyles(); buildImages();
  schedule();
}
function translate() {
  document.documentElement.lang = lang;
  $('style-new').placeholder = t('style-name-ask');
  document.title = `RaspyDarts · ${t('menu-custom')}`;
  document.querySelectorAll('[data-t]').forEach(node => { node.innerHTML = t(node.dataset.t); });
  buildThemes();
  buildAll();
}

// ------------------------------------------------------------------ apercu : clic, fleches, glisser
function canvasPoint(event) {
  const canvas = $('preview');
  const box = canvas.getBoundingClientRect();
  return [(event.clientX - box.left) * canvas.width / box.width, (event.clientY - box.top) * canvas.height / box.height];
}
function zoneAt(point) {
  if (!lastDraw) return null;
  // Le bouton selectionne d'abord (dessine au-dessus), puis les autres
  const entries = Object.entries(lastDraw.zones).sort((a, b) => (Number(b[0]) === selected) - (Number(a[0]) === selected));
  for (const [index, rect] of entries) {
    if (rect && point[0] >= rect[0] && point[0] <= rect[0] + rect[2] && point[1] >= rect[1] && point[1] <= rect[1] + rect[3]) return Number(index);
  }
  return null;
}
let dragging = null;
$('preview').addEventListener('mousedown', (event) => {
  const point = canvasPoint(event);
  const index = zoneAt(point);
  if (!index) return;
  selected = index;
  const ids = shownIds();
  if (ids[index - 1]) {
    current = ids[index - 1];
    const button = menuButtons(screen).find(b => R.buttonId(b) === current);
    if (button && L.isDict(button.place)) dragging = { start: point, place: Object.assign({}, button.place) };
    buildButtons();
  }
  schedule();
});
window.addEventListener('mousemove', (event) => {
  if (!dragging) return;
  const point = canvasPoint(event);
  const [W, H] = previewSize();
  const dx = point[0] - dragging.start[0], dy = point[1] - dragging.start[1];
  const units = new L.Units([W, H], reference());
  const toFile = (px, axis) => reference() ? Math.round(px * (axis === 'x' ? reference()[0] / W : reference()[1] / H))
    : Math.round(px / (axis === 'x' ? W : H) * 10000) / 10000;
  const x0 = units.length(dragging.place.x || 0, 'x'), y0 = units.length(dragging.place.y || 0, 'y');
  editButton(b => { b.place = Object.assign({}, dragging.place, { x: toFile(x0 + dx, 'x'), y: toFile(y0 + dy, 'y') }); });
  schedule();
});
window.addEventListener('mouseup', () => { if (dragging) { dragging = null; changed(); buildButtonForm(); } });
$('preview').setAttribute('tabindex', '0');
$('preview').addEventListener('keydown', (event) => {
  if (!lastDraw) return;
  const count = lastDraw.count || 1;
  if (['ArrowDown', 'ArrowRight'].includes(event.key)) selected = selected % count + 1;
  else if (['ArrowUp', 'ArrowLeft'].includes(event.key)) selected = (selected - 2 + count) % count + 1;
  else return;
  event.preventDefault();
  const ids = shownIds();
  if (ids[selected - 1]) { current = ids[selected - 1]; buildButtons(); }
  schedule();
});

// ------------------------------------------------------------------ evenements
$('lang').addEventListener('change', () => { lang = $('lang').value; store('lang', lang); translate(); });
$('new-file').addEventListener('click', () => { if (confirm(t('new-confirm'))) { user = {}; current = null; styleName = null; buildAll(); } });
$('open-file').addEventListener('change', (e) => { if (e.target.files[0]) openFile(e.target.files[0]); e.target.value = ''; });
$('download').addEventListener('click', download);
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
$('theme').addEventListener('change', () => { store('theme', $('theme').value); $('own-theme').classList.toggle('hidden', $('theme').value !== 'own'); buildButtonForm(); schedule(); });
$('theme-folder').addEventListener('change', (e) => loadTheme([...e.target.files]));
$('preview-res').addEventListener('change', () => { store('preview', $('preview-res').value); schedule(); });
$('fav-games').addEventListener('change', schedule);
$('btn-add').addEventListener('click', addButton);
$('btn-up').addEventListener('click', () => moveButton(-1));
$('btn-down').addEventListener('click', () => moveButton(1));
$('btn-del').addEventListener('click', deleteButton);
$('btn-reset').addEventListener('click', resetMenu);
$('style-name').addEventListener('change', () => { styleName = $('style-name').value; buildStyles(); });
$('style-add').addEventListener('click', addStyle);
$('style-del').addEventListener('click', deleteStyle);
$('images-load').addEventListener('change', (e) => { loadImages([...e.target.files]); e.target.value = ''; });

// ------------------------------------------------------------------ demarrage
const browser = (navigator.language || 'fr').slice(0, 2);
lang = stored('lang') || (LANGS.includes(browser) ? browser : 'en');
$('lang').value = lang;
try { const saved = JSON.parse(stored('file') || '{}'); if (L.isDict(saved)) user = saved; } catch (e) { user = {}; }
screen = stored('screen') || 'main';
if (!screens().includes(screen)) screen = 'main';
translate();
