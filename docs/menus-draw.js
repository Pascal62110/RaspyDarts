// Apercu des menus dans un canvas : le dessin du jeu reproduit au plus pres (include/cscreen.py :
// display_background, classic_header, menu_item/st_item, display_button, logo_item ;
// include/cmenustyle.py : Painter). Les placements viennent de menus-layout.js (identiques au jeu).
(function (root) {
  'use strict';
  const L = root.MenusLayout;
  const ALPHA = 210;   // Screen.alpha

  // ------------------------------------------------------------------ ressources
  const images = {};   // url -> HTMLImageElement (charge)
  let onLoaded = null;
  function image(url) {
    if (!url) return null;
    let img = images[url];
    if (!img) {
      img = new Image();
      img.onload = () => { if (onLoaded) onLoaded(); };
      img.onerror = () => { img.failed = true; };
      img.src = url;
      images[url] = img;
    }
    return (img.complete && img.naturalWidth && !img.failed) ? img : null;
  }
  const fontsLoaded = {};
  function fontFamily(file) {
    // Une police (fichier .ttf) chargee une fois : son nom de famille dans le canvas
    if (!file) return 'sans-serif';
    const family = 'rd_' + file.replace(/[^A-Za-z0-9]/g, '_');
    if (!fontsLoaded[family]) {
      fontsLoaded[family] = 'loading';
      const url = (root.MenusDraw.fontUrl || (f => f))(file);
      if (url) {
        const face = new FontFace(family, `url(${url})`);
        face.load().then(f => { document.fonts.add(f); fontsLoaded[family] = 'ok'; if (onLoaded) onLoaded(); })
          .catch(() => { fontsLoaded[family] = 'failed'; });
      }
    }
    return fontsLoaded[family] === 'ok' ? family : 'sans-serif';
  }

  // ------------------------------------------------------------------ couleurs, textes
  function rgba(color, alpha) {
    if (!color) return 'rgba(0,0,0,0)';
    const a = color.length > 3 ? color[3] / 255 : 1;
    const al = alpha === undefined ? a : alpha / 255 * a;
    return `rgba(${color[0]},${color[1]},${color[2]},${al})`;
  }
  // Screen.menu_color : composantes multipliees (1.5 : plus clair), une rangee sur deux
  function menuColor(color, div, index) {
    if (div === undefined) div = 1.5;
    if (index === undefined || index === null || index % 2 === 1) {
      return color.slice(0, 3).map(c => Math.trunc(Math.min(255, c * div)));
    }
    return color;
  }

  function Context(canvas, setup) {
    // setup : {width, height, colors (colorset), font, language, texts, resolution, imageUrl(path)}
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    Object.assign(this, setup);
    const W = this.width, H = this.height;
    this.res_x = W; this.res_y = H;
    this.res_x_16 = Math.trunc(W / 16); this.res_y_16 = Math.trunc(H / 16);
    this.res_y_15 = Math.trunc(H / 15);
    this.margin = Math.trunc(H / 200);
    this.mid_x = Math.trunc(W / 2);
  }
  Context.prototype.color = function (value, fallback) {
    // Une couleur du theme (Colorset), '#RRGGBB(AA)' ou une liste
    if (value === null || value === undefined || value === false) return fallback === undefined ? null : fallback;
    if (Array.isArray(value)) return value.map(Number);
    const text = String(value);
    // 'menu-buttons*1.5' : une couleur du theme plus claire (ou plus foncee sous 1), comme les boutons classiques
    if (text.includes('*')) {
      const [name, factor] = text.split('*');
      const base = this.color(name.trim(), null);
      const f = parseFloat(factor);
      return base && !isNaN(f) ? base.slice(0, 3).map(c => Math.trunc(Math.min(255, c * f))) : (fallback === undefined ? [128, 128, 128] : fallback);
    }
    if (text.startsWith('#') && (text.length === 7 || text.length === 9)) {
      const parts = [];
      for (let i = 1; i < text.length; i += 2) parts.push(parseInt(text.slice(i, i + 2), 16));
      return parts.some(isNaN) ? (fallback === undefined ? [128, 128, 128] : fallback) : parts;
    }
    const c = this.colors[text];
    return Array.isArray(c) ? c : (fallback === undefined ? [128, 128, 128] : fallback);
  };
  Context.prototype.translate = function (key) {
    if (key === null || key === undefined) return '';
    const texts = this.texts || {};
    return texts[key] !== undefined ? texts[key] : String(key);
  };
  Context.prototype.setFont = function (file, size, bold) {
    this.ctx.font = `${bold ? 'bold ' : ''}${size}px "${fontFamily(file || this.font)}"`;
  };
  Context.prototype.measure = function (text) {
    const m = this.ctx.measureText(text);
    const ascent = m.fontBoundingBoxAscent !== undefined ? m.fontBoundingBoxAscent : m.actualBoundingBoxAscent;
    const descent = m.fontBoundingBoxDescent !== undefined ? m.fontBoundingBoxDescent : m.actualBoundingBoxDescent;
    return { w: Math.ceil(m.width), h: Math.ceil(ascent + descent), ascent: ascent };
  };
  // Screen.scale_text : la taille la plus grande qui tient dans la boite
  Context.prototype.scaleText = function (text, width, height, font, divider) {
    if (divider === undefined) divider = 1.5;
    for (let i = 0; i < 400; i++) {
      const size = Math.trunc(height / divider);
      if (size <= 0) return null;
      this.setFont(font, size);
      const m = this.measure(text);
      if (m.w < width && m.h < height) return [size, Math.trunc((width - m.w) / 2), Math.trunc((height - m.h) / 2), m.w, m.h];
      divider += 0.1;
    }
    return null;
  };
  // Screen.blit_text : texte a la meilleure taille dans une boite
  Context.prototype.blitText = function (text, x, y, w, h, color, opts) {
    opts = opts || {};
    if (text === null || text === undefined || text === '') return;
    text = this.translate(String(text));
    const margin = opts.margin === false ? 0 : this.margin;
    const font = opts.font || this.font;
    const scaled = this.scaleText(text, w - 2 * margin, h - 2 * margin, font, opts.divider);
    if (!scaled) return;
    this.setFont(font, scaled[0]);
    const m = this.measure(text);
    const align = opts.align || 'Center';
    let tx;
    if (align === 'Center') tx = Math.trunc(x + (w - scaled[3] + margin) / 2);
    else if (align === 'Left') tx = Math.trunc(x + margin);
    else tx = Math.trunc(x + w - scaled[3] - 2 * margin);
    const ty = (opts.valign === 'top') ? Math.trunc(y + margin) : Math.trunc(y + scaled[2] + margin);
    this.ctx.fillStyle = rgba(color);
    this.ctx.textBaseline = 'alphabetic';
    this.ctx.fillText(text, tx, ty + m.ascent);
  };
  Context.prototype.roundRect = function (rect, radii, fill, stroke, lineWidth) {
    // pygame.draw.rect avec rayons par coin [haut-gauche, haut-droit, bas-droit, bas-gauche]
    const ctx = this.ctx;
    const [x, y, w, h] = rect;
    const max = Math.max(0, Math.min(w, h) / 2);
    const r = radii.map(v => Math.max(0, Math.min(max, v || 0)));
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x, y, w, h, r); else ctx.rect(x, y, w, h);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) {
      ctx.beginPath();
      const half = lineWidth / 2;
      const inner = r.map(v => Math.max(0, v - half));
      if (ctx.roundRect) ctx.roundRect(x + half, y + half, w - lineWidth, h - lineWidth, inner);
      else ctx.rect(x + half, y + half, w - lineWidth, h - lineWidth);
      ctx.strokeStyle = stroke; ctx.lineWidth = lineWidth; ctx.stroke();
    }
  };
  function radiiOf(corners, radius) {
    const tl = ['Top', 'TopLeft', 'Left', 'All', 'NotTopRight', 'NotBottomLeft', 'NotBottomRight'].includes(corners) ? radius : 0;
    const tr = ['Top', 'TopRight', 'Right', 'All', 'NotTopLeft', 'NotBottomLeft', 'NotBottomRight'].includes(corners) ? radius : 0;
    const bl = ['Bottom', 'BottomLeft', 'Left', 'All', 'NotTopLeft', 'NotTopRight', 'NotBottomRight'].includes(corners) ? radius : 0;
    const br = ['Bottom', 'BottomRight', 'Right', 'All', 'NotTopLeft', 'NotTopRight', 'NotBottomLeft'].includes(corners) ? radius : 0;
    return [tl, tr, br, bl];
  }
  function adaptCorners(corners, operation) {
    if (operation === 'AddRight') {
      if (corners === 'All') return corners;
      if (corners === 'Top') return 'NotBottomLeft';
      if (corners === 'Bottom') return 'NotTopLeft';
      if (corners === 'None') return 'Right';
    }
    return corners;
  }
  function computeCorners(id, total, selected, collapsed, alternate) {
    const offset = alternate ? 2 : 1;
    if (!collapsed) return 'All';
    if (id === selected - offset) return id <= offset ? 'All' : 'Bottom';
    if (id === selected + offset) return id > total - offset ? 'All' : 'Top';
    if (id <= offset) return 'Top';
    if (id > total - offset) return 'Bottom';
    return 'None';
  }
  Context.prototype.radiusSetting = function (height, key) {
    const value = this.colors[key || 'border-radius'];
    return value === 'max' ? Math.trunc(height / 2) : Math.trunc(Number(value) || 0);
  };
  // Screen.new_blit_rect2
  Context.prototype.blitRect2 = function (rect, bg, opts) {
    opts = opts || {};
    if (!bg) return;
    const alpha = opts.alpha === undefined ? ALPHA : opts.alpha;
    let radius = opts.radius === undefined ? this.radiusSetting(rect[3]) : opts.radius;
    const radii = radiiOf(opts.corners || null, radius);
    const padding = opts.padding || 0, border = opts.borderSize || 0;
    if (padding + border > 0 && opts.borderColor) {
      this.roundRect(rect, radii, null, rgba(opts.borderColor, alpha), border);
    }
    if (padding + border > 0) {
      const m = border + padding;
      this.roundRect([rect[0] + m, rect[1] + m, rect[2] - 2 * m, rect[3] - 2 * m], radii, rgba(bg, alpha));
    } else {
      this.roundRect(rect, radii, rgba(bg, alpha));
    }
  };
  Context.prototype.blitBorder = function (rect, color, size, corners, radius) {
    if (!color) return;
    if (radius === undefined) radius = this.radiusSetting(rect[3]);
    this.roundRect(rect, radiiOf(corners, radius), null, rgba(color, ALPHA), size);
  };

  // ------------------------------------------------------------------ ecran classique
  Context.prototype.background = function (block) {
    const ctx = this.ctx;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, this.width, this.height);
    if (block !== undefined && block !== null) {
      // Fond du fichier de menus : Painter.background, cover par defaut
      const settings = (typeof block === 'string') ? (/[/.]/.test(block) && /\.(png|jpe?g|webp)$/i.test(block) ? { image: block } : { color: block })
        : block;
      this.paintBackground(L.merge({ fit: 'cover' }, settings), [0, 0, this.width, this.height], 0, 'rectangle');
      return;
    }
    const img = image(this.imageUrl(this.themeBackground));
    if (img) ctx.drawImage(img, 0, 0, this.width, this.height);
  };
  Context.prototype.version = function () {
    this.blitText('V4.6', this.width - this.res_x_16, Math.trunc(this.height * 3 / 4) - this.res_y_16,
                  this.res_x_16, this.res_y_16, this.color('menu-text-white'), { font: 'Impact.ttf' });
  };
  Context.prototype.info = function (items) {
    const c = this.color('menu-text-black');
    if (items.includes('version')) {
      this.blitText('V4.6.1_20261016', this.margin, this.height * 1.05 / 30, this.width * 1.9 / 16, this.height * 0.9 / 30, c,
                    { align: 'Left', margin: false });
    }
    if (items.includes('rpi_version')) {
      this.blitText('Pi 3 Model B Plus Rev 1.3', this.width * 3 / 4, this.height * 1.05 / 30, this.width / 4 - this.margin,
                    this.height * 0.9 / 30, c, { align: 'Right', margin: false });
    }
    if (items.includes('ips')) {
      this.blitText('192.168.1.120', this.width * 3 / 4, this.height * 2.05 / 30, this.width / 4 - this.margin,
                    this.height * 0.9 / 30, c, { align: 'Right', margin: false });
      this.blitText('192.168.1.120', 0, this.height * 2.05 / 30, this.width / 4 - this.margin, this.height * 0.9 / 30, c,
                    { align: 'Left', margin: false });
    }
  };
  // Screen.classic_header
  Context.prototype.classicHeader = function (text, subtext) {
    const rect = [0, Math.trunc(this.height / 30), this.width, Math.trunc(this.height / 15)];
    const header = this.color('menu-header', null);
    if (header) this.blitRect2(rect, header);
    if (text) this.blitText(text, rect[0], rect[1], rect[2], rect[3], this.color('menu-text'));
    if (subtext) {
      rect[1] += rect[3];
      if (header) this.blitRect2(rect, header, { alpha: 255 });
      this.blitText(subtext, rect[0], rect[1], rect[2], rect[3], this.color('menu-text'));
    }
    return rect;
  };
  // Screen.menu_item (texte seul : BTN_CHOICE) : rectangle de la rangee
  Context.prototype.menuItemRect = function (index, total, space, tabs) {
    let minY = total > 8 ? 2 * this.res_y_16 : 3 * this.res_y_16;
    if (tabs) minY += this.res_y_16;
    const maxY = this.height - 3 * this.res_y_16 - minY;   // exit=False
    const collapsed = total >= 10;
    const verticalMargin = collapsed ? 0 : Math.trunc(maxY / 72);
    const height = Math.min(this.res_y_15, Math.trunc(maxY / total));
    const posX = Math.trunc(this.width * 5 / 16);
    const width = Math.trunc(this.width / 2 - this.res_x_16 - height);
    const posY = Math.trunc(minY + (verticalMargin + height) * (index + space - 1));
    return { rect: [posX, posY, width, height], collapsed: collapsed };
  };
  Context.prototype.menuItem = function (index, total, selected, label, text, opts) {
    opts = opts || {};
    const { rect, collapsed } = this.menuItemRect(index, total, opts.space || 0, opts.tabs);
    const sel = index === selected;
    let shortcutBg, shortcutText = this.color('menu-text-black'), textBg, valueText;
    let border = null, borderSize = 0, padding = 0, corners;
    if (sel) {
      shortcutBg = this.color('menu-selected'); valueText = this.color('menu-text-white');
      textBg = this.color('menu-selected'); border = this.color('menu-border');
      borderSize = Math.trunc(Number(this.colors['border-size']) || 0); padding = Math.trunc(Number(this.colors.padding) || 0);
      corners = 'All';
    } else {
      shortcutBg = this.color('menu-shortcut');
      textBg = collapsed ? menuColor(this.color('menu-buttons'), 0.5, index + 1) : menuColor(this.color('menu-buttons'));
      valueText = collapsed ? menuColor(this.color('menu-text-black'), 1.5, index + 1) : this.color('menu-text-black');
      corners = computeCorners(index, total, selected, collapsed);
    }
    if (opts.valid === false && !sel) {
      textBg = this.color('menu-inactive'); valueText = [150, 150, 150];
    }
    this.stItem([shortcutBg, label, shortcutText], [textBg, text, valueText], rect, padding, borderSize, border, corners);
    return rect;
  };
  // Screen.st_item : raccourci | texte
  Context.prototype.stItem = function (shortcut, text, rect, padding, borderSize, borderColor, corners) {
    const pict = this.colors['main-sub-menu-shortcuts'];
    const alignText = this.colors['main-sub-menu-text-align'] || 'Left';
    const sRect = [rect[0], rect[1], rect[3], rect[3]];
    const tRect = [rect[0] + rect[3], rect[1], rect[2] - rect[3], rect[3]];
    if (borderSize + padding > 0) {
      const minus = borderSize + padding;
      let radius = this.colors['border-radius'] === 'max' ? Math.trunc(rect[3] / 2) - minus : Math.trunc(Number(this.colors['border-radius'])) - minus;
      radius = Math.max(radius, 0);
      if (borderColor) this.blitBorder(rect, borderColor, borderSize, corners);
      const inside = [rect[0] + minus, rect[1] + minus, rect[2] - 2 * minus, rect[3] - 2 * minus];
      this.blitRect2(inside, text[0], { corners: corners, radius: radius });
      if (shortcut[1] !== null && shortcut[1] !== undefined && pict !== null && pict !== undefined) {
        const box = [inside[0], inside[1], inside[3] + minus, inside[3]];
        this.blitRect2(box, shortcut[0], { corners: adaptCorners(corners, 'AddRight'), radius: radius });
        this.blitText(pict !== '' ? pict : shortcut[1], ...sRect, shortcut[2]);
        this.blitText(text[1], ...tRect, text[2], { align: alignText });
      } else {
        this.blitText(text[1], ...rect, text[2], { align: alignText });
      }
    } else if (shortcut[1] === null || shortcut[1] === undefined || pict === null || pict === undefined) {
      this.blitRect2(rect, text[0], { corners: corners });
      this.blitText(text[1], ...rect, text[2], { align: alignText });
    } else {
      this.blitRect2(rect, text[0], { corners: adaptCorners(corners, 'All') });
      this.blitText(text[1], ...tRect, text[2], { align: alignText });
      this.blitRect2(sRect, shortcut[0], { corners: 'All' });
      this.blitText(pict !== '' ? pict : shortcut[1], ...sRect, shortcut[2]);
    }
  };
  // Screen.display_button : boutons du bas (Retour, Enregistrer...)
  Context.prototype.footerButton = function (selected, text, special) {
    const width = Math.trunc(this.width / 8);
    let posX;
    if (special === 'tab1' || special === 'escape') posX = Math.trunc(this.width / 8);
    else if (special === 'tab2' || special === 'refresh') posX = Math.trunc(this.width / 2 - width / 2);
    else posX = Math.trunc(this.width * 7 / 8 - width);
    const posY = special.startsWith('tab') ? Math.trunc(this.height / 32 * 3.5) : Math.trunc(this.height / 32 * 29);
    const height = this.res_y_16;
    const rect = [posX, posY, width, height];
    let bg, textColor, border = null, borderSize = 0, padding = 0;
    if (selected) {
      bg = this.color('menu-selected'); textColor = this.color('menu-text-white'); border = this.color('menu-border');
      borderSize = Number(this.colors['border-size']) || 0; padding = Number(this.colors.padding) || 0;
    } else {
      bg = this.color('menu-buttons'); textColor = this.color('menu-text-black');
    }
    const radius = this.colors['button-radius'] === 'max' ? Math.trunc(height / 2) : Math.min(Math.trunc(height / 2), Math.trunc(Number(this.colors['button-radius'])));
    this.blitRect2(rect, bg, { padding: padding, borderColor: border, borderSize: borderSize, corners: 'All', radius: radius });
    this.blitText(text, ...rect, textColor);
    return rect;
  };
  // Screen.logo_item : les tuiles classiques (logos)
  Context.prototype.logoItem = function (index, total, selected, logoUrl, perLine, align, opts) {
    opts = opts || {};
    let posX, maxX;
    if (align === 'Left') { posX = Math.trunc(this.res_x_16 / 2); maxX = 8 * this.res_x_16 - posX; }
    else { posX = 3 * this.res_x_16; maxX = 13 * this.res_x_16; }
    const maxW = maxX - posX;
    let posY = 3 * this.res_y_16;
    const maxH = 13 * this.res_y_16 - posY;
    const perCol = Math.trunc(total / perLine) + 1;
    const height = Math.trunc(maxW / (perLine + 1));
    posX += (maxW - perLine * height) / 2;
    if (opts.menu) posY = (this.height - height) / 2;
    else posY += (maxH - perCol * height) / 2;
    posY += Math.trunc((index - 1) / perLine) * height;
    posX += ((index - 1) % perLine) * height;
    let radius = opts.radius === undefined ? 50 : opts.radius;
    let selectedColor = this.color('menu-selected'), borderColor = this.color('menu-border');
    if (opts.available === false) { selectedColor = this.color('menu-warning'); borderColor = selectedColor; }
    const rect = [Math.trunc(posX), Math.trunc(posY), height, height];
    if (index === selected) {
      const bs = Number(this.colors['border-size']) || 0, pad = Number(this.colors.padding) || 0;
      if (bs + pad > 0) {
        this.blitBorder(rect, borderColor, bs, 'All', radius);
        const inner = [rect[0] + bs + pad, rect[1] + bs + pad, height - 2 * (bs + pad), height - 2 * (bs + pad)];
        this.blitRect2(inner, selectedColor, { corners: 'All', radius: radius - pad - bs });
      } else {
        this.blitRect2(rect, selectedColor, { corners: 'All', radius: radius });
      }
    } else {
      this.blitRect2(rect, this.color('menu-inactive'), { alpha: 20, corners: 'All', radius: radius });
    }
    const img = image(logoUrl);
    if (img) {
      if (opts.available === false) { this.ctx.save(); this.ctx.filter = 'grayscale(1)'; }
      this.ctx.drawImage(img, rect[0], rect[1], height, height);
      if (opts.available === false) this.ctx.restore();
    }
    return rect;
  };

  // ------------------------------------------------------------------ styles (Painter)
  const STATES = ['selected', 'disabled', 'pressed'];
  Context.prototype.stateStyle = function (style, state) {
    let values = L.merge(root.MenusDraw.styleDefaults, style || {});
    if (STATES.includes(state)) values = L.merge(values, values[state] || {});
    return values;
  };
  Context.prototype.scaleOf = function (style, state) {
    const v = this.stateStyle(style, state);
    const s = parseFloat(v.scale || 1.0);
    return isNaN(s) ? 1.0 : Math.max(0.5, Math.min(2.0, s));
  };
  Context.prototype.placed = function (rect, style, state) {
    let r = rect.slice();
    const scale = this.scaleOf(style, state);
    if (scale !== 1.0) {
      const cx = r[0] + Math.trunc(r[2] / 2), cy = r[1] + Math.trunc(r[3] / 2);
      const w = Math.max(1, Math.trunc(r[2] * scale)), h = Math.max(1, Math.trunc(r[3] * scale));
      r = [cx - Math.trunc(w / 2), cy - Math.trunc(h / 2), w, h];
    }
    return r;
  };
  Context.prototype.shapeOf = function (values, height, units) {
    const shape = String(values.shape || 'rounded');
    const radius = values.radius === undefined ? 0.25 : values.radius;
    let r;
    if (shape === 'pill') r = Math.trunc(height / 2);
    else if (shape === 'rectangle') r = 0;
    else r = parseFloat(radius) <= 1 ? Math.trunc(parseFloat(radius) * height) : Math.trunc(units.length(radius, 'y'));
    return [shape, r];
  };
  Context.prototype.fillImage = function (img, rect, block) {
    const ctx = this.ctx;
    const [x, y, w, h] = rect;
    const fit = String(block.fit || 'stretch');
    const iw = img.naturalWidth, ih = img.naturalHeight;
    const anchor = L.ANCHORS[String(block.position || 'center')] || [0.5, 0.5];
    const offset = block.offset || [0, 0];
    if (fit === 'stretch') { ctx.drawImage(img, x, y, w, h); return; }
    if (fit === 'cover' || fit === 'contain' || fit === 'center') {
      let ratio;
      if (fit === 'cover') ratio = Math.max(w / iw, h / ih);
      else if (fit === 'contain') ratio = Math.min(w / iw, h / ih);
      else { const part = block.size || [1, 1]; ratio = Math.min(w * part[0] / iw, h * part[1] / ih); }
      const sw = Math.max(1, Math.trunc(iw * ratio)), sh = Math.max(1, Math.trunc(ih * ratio));
      const px = (w - sw) * anchor[0] + parseFloat(offset[0]) * w, py = (h - sh) * anchor[1] + parseFloat(offset[1]) * h;
      ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
      ctx.drawImage(img, x + Math.trunc(px), y + Math.trunc(py), sw, sh);
      ctx.restore();
      return;
    }
    if (fit === 'tile') {
      ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
      for (let px = 0; px < w; px += iw) for (let py = 0; py < h; py += ih) ctx.drawImage(img, x + px, y + py);
      ctx.restore();
      return;
    }
    if (fit === 'slice') {
      const b = Math.max(1, Math.min(parseInt(block.slice || 12, 10), Math.trunc(iw / 2) - 1, Math.trunc(ih / 2) - 1, Math.trunc(w / 2), Math.trunc(h / 2)));
      const xs = [[0, b, 0, b], [b, iw - 2 * b, b, w - 2 * b], [iw - b, b, w - b, b]];
      const ys = [[0, b, 0, b], [b, ih - 2 * b, b, h - 2 * b], [ih - b, b, h - b, b]];
      for (const [sx, sw, tx, tw] of xs) for (const [sy, sh, ty, th] of ys) {
        if (tw > 0 && th > 0 && sw > 0 && sh > 0) ctx.drawImage(img, sx, sy, sw, sh, x + tx, y + ty, tw, th);
      }
    }
  };
  Context.prototype.paintBackground = function (block, rect, radius, shape) {
    if (typeof block === 'string') {
      block = (/\.(png|jpe?g|webp)$/i.test(block) || block.includes('/')) ? { image: block } : { color: block };
    }
    block = block || {};
    if (shape === 'none') return;
    const ctx = this.ctx;
    const opacity = block.opacity === undefined || block.opacity === null ? 1.0 : parseFloat(block.opacity);
    ctx.save();
    ctx.globalAlpha = Math.max(0, Math.min(1, opacity));
    const radii = [radius, radius, radius, radius];
    const color = this.color(block.color, null);
    if (color) this.roundRect(rect, radii, rgba(color));
    const img = block.image ? image(this.imageUrl(block.image)) : null;
    if (img) {
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(rect[0], rect[1], rect[2], rect[3], radii); else ctx.rect(...rect);
      ctx.clip();
      this.fillImage(img, rect, block);
    }
    ctx.restore();
  };
  Context.prototype.styledText = function (text, rect, settings, units, zoom) {
    if (!text) return;
    if (zoom === undefined) zoom = 1;
    // size: auto : comme les boutons classiques, le texte suit la hauteur de sa place
    const auto = String(settings.size).trim().toLowerCase() === 'auto';
    if (!auto && parseFloat(settings.size || 0) <= 0) return;
    let size = auto ? Math.max(1, Math.trunc(rect[3] * 0.84 / 1.5 * zoom)) : Math.max(1, Math.trunc(units.text(settings.size || '4.5%') * zoom));
    const font = settings.font || this.font;
    const color = this.color(settings.color, [0, 0, 0]);
    const bold = !!settings.bold;
    let m;
    for (;;) {
      this.setFont(font, size, bold);
      m = this.measure(text);
      if (m.w <= rect[2] * 0.94 || size <= 6) break;
      size = Math.trunc(size * 0.9);
    }
    const position = String(settings.position || 'center');
    const anchor = L.ANCHORS[position] || [0.5, 0.5];
    let align = String(settings.align || 'center');
    if (align === 'theme') align = String(this.colors['main-sub-menu-text-align'] || 'Left').toLowerCase();
    const horizontal = ['center', 'top', 'bottom'].includes(position) ? ({ left: 0, right: 1 }[align] !== undefined ? { left: 0, right: 1 }[align] : anchor[0]) : anchor[0];
    const margin = rect[3] * 0.08;
    const offset = settings.offset || [0, 0];
    const px = rect[0] + margin + (rect[2] - 2 * margin - m.w) * horizontal + parseFloat(offset[0]) * rect[2];
    const py = rect[1] + margin + (rect[3] - 2 * margin - m.h) * anchor[1] + parseFloat(offset[1]) * rect[3];
    const ctx = this.ctx;
    ctx.textBaseline = 'alphabetic';
    if (settings.shadow) {
      const shift = Math.max(1, Math.trunc(size / 20));
      ctx.fillStyle = 'rgba(0,0,0,0.59)';
      ctx.fillText(text, Math.trunc(px) + shift, Math.trunc(py) + shift + m.ascent);
    }
    ctx.fillStyle = rgba(color.slice(0, 3));
    ctx.fillText(text, Math.trunc(px), Math.trunc(py) + m.ascent);
  };
  // Painter.draw_button
  Context.prototype.styledButton = function (rect0, style, text, icon, state, units, shortcut, shortcuts) {
    shortcuts = shortcuts || {};
    const values = this.stateStyle(style, state);
    const zoom = this.scaleOf(style, state);
    const rect = this.placed(rect0, style, state);
    const [w, h] = [rect[2], rect[3]];
    const [shape, radius] = this.shapeOf(values, h, units);
    const ctx = this.ctx;
    if (values.shadow && shape !== 'none') {
      const shift = Math.max(2, Math.trunc(h / 25));
      this.roundRect([rect[0] + shift, rect[1] + shift, w, h], [radius, radius, radius, radius], 'rgba(0,0,0,0.35)');
    }
    this.paintBackground(values.background, rect, radius, shape);
    const border = values.border || {};
    if (parseInt(border.width || 0, 10) > 0 && shape !== 'none') {
      this.roundRect(rect, [radius, radius, radius, radius], null, rgba(this.color(border.color, [0, 0, 0])), parseInt(border.width, 10));
    }
    let textRect = rect.slice();
    if (shortcut) {
      const position = String(shortcuts.position || 'left');
      const part = shortcuts.size || (['left', 'right'].includes(position) ? 0.4 : 0.15);
      // Sur un cote : une case de la hauteur du bouton, au plus le quart de sa largeur (boutons hauts, tuiles)
      const tall = Math.min(h, Math.floor(w / 4));
      const side = Math.trunc((['left', 'right'].includes(position) ? tall : h) * Math.min(1, Math.max(0.05, parseFloat(part))));
      // Sa case : la couleur des raccourcis du theme (null : la touche seule)
      const fill = shortcuts.background === undefined ? 'menu-shortcut' : shortcuts.background;
      const label = { size: side / units.height, font: shortcuts.font, bold: shortcuts.bold,
                      color: shortcuts.color || (fill ? 'menu-text-black' : 'menu-shortcut'), position: 'center' };
      let box;
      if (position === 'left' || position === 'right') {
        box = [0, Math.floor((h - tall) / 2), Math.trunc(tall * 1.1), tall];
        if (position === 'right') { box[0] = w - box[2]; textRect = [rect[0], rect[1], box[0], h]; }
        else textRect = [rect[0] + box[2], rect[1], w - box[2], h];
      } else {
        const anchor = L.ANCHORS[position] || [0, 0];
        box = [0, 0, Math.trunc(side * 2.2), Math.trunc(side * 1.3)];
        box[0] = Math.trunc((w - box[2]) * anchor[0]); box[1] = Math.trunc((h - box[3]) * anchor[1]);
      }
      if (fill) {
        const inset = Math.max(1, Math.floor(box[3] / 10));
        const cell = [rect[0] + box[0] + inset, rect[1] + box[1] + inset, box[2] - 2 * inset, box[3] - 2 * inset];
        this.paintBackground({ color: fill }, cell, Math.floor(radius * cell[3] / Math.max(1, h)),
                             ['none', 'pill'].includes(shape) ? 'rounded' : shape);
      }
      this.styledText(shortcut, [rect[0] + box[0], rect[1] + box[1], box[2], box[3]], label, new L.Units([units.width, units.height]));
    }
    const img = icon ? image(this.imageUrl(icon)) : null;
    if (icon) {
      const settings = values.icon || {};
      let side = Math.trunc(Math.min(w, h) * parseFloat(settings.size || 0.7));
      const position = String(settings.position || 'left');
      let bx, by;
      const tx = textRect[0] - rect[0];
      if (!text) {
        // Une icone seule (un logo) : au milieu de la place laissee par le raccourci
        side = Math.trunc(Math.min(textRect[2], textRect[3]) * parseFloat(settings.size || 0.7));
        bx = tx + Math.floor(textRect[2] / 2) - Math.floor(side / 2);
        by = textRect[1] - rect[1] + Math.floor(textRect[3] / 2) - Math.floor(side / 2);
      } else if (position === 'top') { bx = Math.trunc(w / 2) - Math.trunc(side / 2); by = Math.trunc(h * 0.06); textRect = [rect[0], rect[1] + by + side, w, h - by - side]; }
      else if (position === 'center') { bx = Math.trunc(w / 2) - Math.trunc(side / 2); by = Math.trunc(h / 2) - Math.trunc(side / 2); }
      else if (position === 'right') { bx = w - Math.trunc(h * 0.1) - side; by = Math.trunc(h / 2) - Math.trunc(side / 2); textRect = [rect[0], rect[1], bx, h]; }
      else { bx = tx + Math.trunc(h * 0.1); by = Math.trunc(h / 2) - Math.trunc(side / 2); textRect = [rect[0] + bx + side, rect[1], textRect[0] + textRect[2] - (rect[0] + bx + side), h]; }
      if (img) this.fillImage(img, [rect[0] + bx, rect[1] + by, side, side], { fit: settings.fit || 'contain' });
    }
    this.styledText(text, textRect, values.text || {}, units, zoom);
    return rect;
  };

  root.MenusDraw = { Context: Context, image: image, rgba: rgba, menuColor: menuColor, styleDefaults: {},
                     setOnLoaded: f => { onLoaded = f; }, fontUrl: null };
})(typeof window !== 'undefined' ? window : globalThis);
