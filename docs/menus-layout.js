// Regles de placement des boutons des menus (docs/menu/menus.md, sections 4 et 12) : la meme
// chose, au pixel pres, que include/cmenustyle.py (layout, Units, merge). Un test les compare :
// docs/test_placement.py. Toute modification d'un cote doit etre faite de l'autre.
(function (root) {
  'use strict';

  // Valeurs par defaut en pourcentage : parts de l'ecran, quelle que soit l'unite du fichier
  const LAYOUT_DEFAULTS = {
    list: { area: { x: '25%', y: '18%', width: '50%', height: '72%' }, columns: 1, button_size: { width: 1.0, height: '9%' } },
    grid: { area: { x: '10%', y: '18%', width: '80%', height: '72%' }, columns: 3, button_size: { width: 1.0, height: '9%' } },
    tiles: { area: { x: '10%', y: '18%', width: '80%', height: '72%' }, columns: 3, button_size: { width: 1.0, height: null } }
  };
  const GAP_DEFAULT = { x: '2%', y: '1.5%' };
  const ANCHORS = {
    top_left: [0, 0], top_right: [1, 0], bottom_left: [0, 1], bottom_right: [1, 1],
    center: [0.5, 0.5], top: [0.5, 0], bottom: [0.5, 1], left: [0, 0.5], right: [1, 0.5]
  };

  function isDict(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  // cmenustyle.merge : les valeurs de top sur celles de base, dictionnaire par dictionnaire
  function merge(base, top) {
    if (!isDict(base) || !isDict(top)) {
      return (top !== null && top !== undefined) ? top : base;
    }
    const result = Object.assign({}, base);
    for (const key of Object.keys(top)) {
      const value = top[key];
      result[key] = isDict(value) ? merge(result[key], value) : value;
    }
    return result;
  }

  // Arrondi des regles de placement : 0.5 vers le haut (math.floor(x + 0.5))
  function roundHalfUp(value) {
    return Math.floor(value + 0.5);
  }

  // cmenustyle.Units : fractions de l'ecran, pixels d'une resolution de reference, ou '50%'
  function Units(screenSize, resolution) {
    this.width = screenSize[0];
    this.height = screenSize[1];
    this.reference = (Array.isArray(resolution) && resolution.length === 2) ? resolution : null;
  }
  Units.prototype.length = function (value, axis) {
    const size = axis === 'x' ? this.width : this.height;
    if (typeof value === 'string' && value.trim().endsWith('%')) {
      return parseFloat(value.trim().slice(0, -1)) / 100 * size;
    }
    value = parseFloat(value || 0);
    if (this.reference !== null) {
      return value * size / (axis === 'x' ? this.reference[0] : this.reference[1]);
    }
    return value * size;
  };
  // round() de Python : la moitie va au pair (2.5 -> 2)
  function roundHalfEven(value) {
    const floor = Math.floor(value), diff = value - floor;
    if (Math.abs(diff - 0.5) < 1e-9) return floor % 2 === 0 ? floor : floor + 1;
    return Math.round(value);
  }
  Units.prototype.text = function (value) {
    return Math.max(1, roundHalfEven(this.length(value, 'y')));
  };

  function num(value, fallback) {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? fallback : parsed;
  }

  // Parts d'une colonne : un bouton peut prendre une demie, un tiers, un quart de colonne
  const SUBCELLS = 12;
  function gcd(a, b) { return b ? gcd(b, a % b) : a; }

  // cmenustyle.zones_of : les zones de boutons d'un menu (la sienne, nom '', puis zones:),
  // avec les index (depuis 1) de leurs boutons ; zone inconnue ou absente : la premiere
  function zonesOf(menu, buttons) {
    const extra = {};
    if (isDict(menu.zones)) for (const [name, zone] of Object.entries(menu.zones)) if (isDict(zone)) extra[String(name)] = zone;
    const members = { '': [] };
    for (const name of Object.keys(extra)) members[name] = [];
    buttons.forEach((button, i) => {
      if (button.place) return;
      const name = String(button.zone || '');
      members[name in members ? name : ''].push(i + 1);
    });
    return [['', menu, members['']]].concat(Object.entries(extra).map(([name, zone]) => [name, zone, members[name]]));
  }

  // cmenustyle.layout : rectangles [x, y, w, h] des boutons (index depuis 1), page, pages ;
  // et pour le configurateur, la grille de chaque zone (zones[nom]) et celle de la premiere
  function layout(menu, buttons, screenSize, resolution, selected) {
    if (selected === undefined) selected = 1;
    const units = new Units(screenSize, resolution);
    const rects = {}, zones = {};
    let page = 0, pages = 0;
    for (const [name, zone, members] of zonesOf(menu, buttons)) {
      const found = layoutZone(zone, buttons, members, units, selected);
      Object.assign(rects, found.rects);
      zones[name] = found;
      if (name === '' || members.includes(selected)) { page = found.page; pages = found.pages; }
    }
    buttons.forEach((button, i) => {
      const place = button.place;
      if (!isDict(place)) return;
      const width = units.length(place.width !== undefined ? place.width : '10%', 'x');
      const height = units.length(place.height !== undefined ? place.height : '8%', 'y');
      const anchor = ANCHORS[String(place.anchor || 'top_left')] || [0, 0];
      const posX = units.length(place.x !== undefined ? place.x : 0, 'x') - anchor[0] * width;
      const posY = units.length(place.y !== undefined ? place.y : 0, 'y') - anchor[1] * height;
      rects[i + 1] = [roundHalfUp(posX), roundHalfUp(posY), roundHalfUp(width), roundHalfUp(height)];
    });
    const first = zones[''];
    return { rects: rects, page: page, pages: pages, zones: zones, rows: first.rows, cells: first.cells, columnW: first.grid.columnW,
             buttonH: first.grid.buttonH, grid: first.grid };
  }

  // cmenustyle.layout_zone : les boutons d'une zone (flowing : leurs index)
  function layoutZone(menu, buttons, flowing, units, selected) {
    const kind = String(menu.layout || 'list');
    const defaults = LAYOUT_DEFAULTS[kind] || LAYOUT_DEFAULTS.list;
    const area = merge(defaults.area, menu.area || {});
    const columns = Math.max(1, parseInt(menu.columns || defaults.columns, 10));
    const size = merge(defaults.button_size, menu.button_size || {});
    const gap = merge(GAP_DEFAULT, menu.gap || {});

    const areaX = units.length(area.x, 'x'), areaY = units.length(area.y, 'y');
    const areaW = units.length(area.width, 'x'), areaH = units.length(area.height, 'y');
    const gapX = units.length(gap.x, 'x'), gapY = units.length(gap.y, 'y');
    const columnW = (areaW - (columns - 1) * gapX) / columns;
    let buttonW = num(size.width, 1) * columnW;
    let buttonH;
    if (size.height !== null && size.height !== undefined) {
      buttonH = units.length(size.height, 'y');
    } else {
      // Tuiles carrees : aussi grandes que leurs rangees tiennent (3 rangees au plus, puis pages)
      const needed = Math.max(1, Math.min(3, Math.ceil(flowing.length / columns)));
      buttonW = buttonH = Math.min(buttonW, (areaH - (needed - 1) * gapY) / needed);
    }
    // Cases de la grille (section 12), en parts de colonne (SUBCELLS) : chaque bouton prend
    // span.columns x span.rows cases (1 x 1 par defaut ; 0.5 : une demi-colonne), a la premiere
    // place libre dans l'ordre de lecture ; plus large que les colonnes : autant qu'il y en a,
    // le bouton plus large et centre dessus. Un bouton a case fixe (cell: {row, column},
    // depuis 0) la prend d'abord ; une rangee vide reste (un espace voulu) ; space_left : un
    // espace vide a sa gauche, en parts de colonne, pris avec ses cases
    const total = columns * SUBCELLS;
    const cells = {};
    const taken = new Set();
    const sizeOf = (index) => {
      const span = isDict(buttons[index - 1].span) ? buttons[index - 1].span : {};
      const wide = Math.max(1, roundHalfUp(num(span.columns || 1, 1) * SUBCELLS));
      const high = Math.max(1, parseInt(span.rows || 1, 10));
      const left = Math.max(0, roundHalfUp(num(buttons[index - 1].space_left || 0, 0) * SUBCELLS));
      return [wide, high, Math.min(wide + left, total), left];
    };
    const free = (row, start, width, high) => {
      const wanted = [];
      for (let r = 0; r < high; r++) for (let c = 0; c < width; c++) wanted.push(`${row + r},${start + c}`);
      return wanted.some(k => taken.has(k)) ? null : wanted;
    };
    for (const index of flowing) {
      const cell = buttons[index - 1].cell;
      if (!isDict(cell)) continue;
      const [wide, high, width, left] = sizeOf(index);
      const row = Math.max(0, parseInt(cell.row || 0, 10));
      const start = Math.min(Math.max(0, roundHalfUp(num(cell.column || 0, 0) * SUBCELLS)), total - width);
      const wanted = free(row, start, width, high);
      if (wanted) { cells[index] = [row, start, width, high, wide, left]; wanted.forEach(k => taken.add(k)); }
    }
    for (const index of flowing) {
      const [wide, high, width, left] = sizeOf(index);
      // Un bouton commence sur ses pas : une colonne entiere au debut d'une colonne, une demie a une demie...
      const step = width % SUBCELLS === 0 ? SUBCELLS : gcd(width, SUBCELLS);
      for (let row = 0; !(index in cells); row++) {
        for (let start = 0; start <= total - width; start += step) {
          const wanted = free(row, start, width, high);
          if (wanted) { cells[index] = [row, start, width, high, wide, left]; wanted.forEach(k => taken.add(k)); break; }
        }
      }
    }
    const count = Math.max(0, ...Object.values(cells).map(c => c[0] + c[3]));
    const rows = [];
    for (let row = 0; row < count; row++) rows.push(flowing.filter(index => cells[index][0] === row));
    // Les rangees liees par un bouton sur plusieurs rangees restent sur la meme page
    const blocks = [];
    let endRow = -1;
    for (let row = 0; row < count; row++) {
      if (row > endRow) blocks.push([]);
      blocks[blocks.length - 1].push(row);
      endRow = Math.max(endRow, ...rows[row].map(index => cells[index][0] + cells[index][3] - 1));
    }
    const spaceOf = (row) => rows[row].reduce((sum, index) => sum + num(buttons[index - 1].space_before, 0), 0) * buttonH;
    const spanWidth = (width) => {
      // Largeur de cases : des colonnes entieres avec leurs ecarts, ou des parts de colonne
      if (width % SUBCELLS === 0) { const whole = width / SUBCELLS; return whole * columnW + (whole - 1) * gapX; }
      return width * (columnW + gapX) / SUBCELLS - gapX;
    };

    // Un seul ecran (overflow: fit, par defaut) : des rangees qui ne tiennent pas dans la zone
    // rendent les boutons plus petits (jamais plus grands), tous sur l'ecran ; jamais de
    // deuxieme page (un bouton ajoute a un menu plein par une nouvelle version...).
    // overflow: pages / scroll : comme avant
    const overflow = String(menu.overflow || 'fit');
    if (overflow === 'fit' && count) {
      let spaces = 0;
      for (let row = 0; row < count; row++) for (const index of rows[row]) spaces += num(buttons[index - 1].space_before, 0);
      const fitting = Math.max(1, (areaH - (count - 1) * gapY) / (count + spaces));
      if (fitting < buttonH) {
        // Les tuiles carrees le restent
        if (size.height === null || size.height === undefined) buttonW = Math.min(buttonW, fitting);
        buttonH = fitting;
      }
    }

    let pages = [], pageRows = [], usedH = 0;
    for (const block of blocks) {
      const height = block.reduce((sum, row) => sum + spaceOf(row), 0) + block.length * buttonH + (block.length - 1) * gapY;
      if (pageRows.length && usedH + height + gapY > areaH + 0.5) {
        pages.push(pageRows);
        pageRows = [];
        usedH = 0;
      }
      usedH += height + (pageRows.length ? gapY : 0);
      pageRows.push(...block);
    }
    if (pageRows.length) pages.push(pageRows);
    const scroll = overflow === 'scroll';
    if (scroll || overflow === 'fit') pages = pages.length ? [[].concat(...pages)] : [];

    let page = 0;
    pages.forEach((rowsOfPage, number) => {
      if (rowsOfPage.some(row => rows[row].includes(selected))) page = number;
    });

    const rects = {}, tops = {};
    if (pages.length) {
      const rowsOfPage = pages[page];
      const heights = rowsOfPage.map((row, position) => spaceOf(row) + (position ? gapY : 0));
      const blockH = heights.reduce((a, b) => a + b, 0) + rowsOfPage.length * buttonH;
      let top = areaY + (String(menu.align || 'center') === 'center' ? (areaH - blockH) / 2 : 0);
      if (scroll && blockH > areaH) {
        const rowOf = Math.max(0, rowsOfPage.findIndex(row => rows[row].includes(selected)));
        const selectedBottom = heights.slice(0, rowOf + 1).reduce((a, b) => a + b, 0) + (rowOf + 1) * buttonH;
        top = areaY - Math.max(0, selectedBottom - areaH);
      }
      let posY = top;
      rowsOfPage.forEach((row, position) => {
        posY += heights[position];
        tops[row] = posY;
        posY += buttonH;
      });
      for (const row of rowsOfPage) {
        // Une rangee de boutons d'une rangee chacun (aucun a case fixe), remplie depuis la
        // gauche : centree dans la zone (une derniere rangee incomplete aussi, un bouton de 2/3...)
        const alone = rows[row].every(index => cells[index][3] === 1 && !isDict(buttons[index - 1].cell)) &&
          !flowing.some(other => cells[other][0] < row && row < cells[other][0] + cells[other][3]);
        const ordered = rows[row].slice().sort((a, b) => cells[a][1] - cells[b][1]);
        let sum = 0;
        const packed = ordered.every(index => { const ok = cells[index][1] === sum; sum += cells[index][2]; return ok; });
        const used = alone && packed ? sum : total;
        let left;
        if (used % SUBCELLS === 0) {
          const filled = used / SUBCELLS;
          left = areaX + (areaW - (filled * columnW + (filled - 1) * gapX)) / 2;
        } else left = areaX + (total - used) * (columnW + gapX) / SUBCELLS / 2;
        for (const index of rows[row]) {
          const [, start0, widthCells0, high, wide0, leftPart] = cells[index];
          // Son espace vide a gauche d'abord
          const start = start0 + leftPart, widthCells = widthCells0 - leftPart;
          // (le bouton plus etroit si la rangee est pleine)
          const wide = leftPart ? Math.min(wide0, widthCells) : wide0;
          const last = row + high - 1;
          const bottom = last in tops ? tops[last] + buttonH : tops[row] + high * buttonH + (high - 1) * gapY;
          const column = Math.floor(start / SUBCELLS), within = start % SUBCELLS;
          const cellsX = left + column * (columnW + gapX) + within * (columnW + gapX) / SUBCELLS;
          const cellsW = spanWidth(widthCells);
          const width = wide % SUBCELLS === 0 ? buttonW + (wide / SUBCELLS - 1) * (columnW + gapX)
            : spanWidth(wide) - (columnW - buttonW) * wide / SUBCELLS;
          const posX = cellsX + (cellsW - width) / 2;
          rects[index] = [roundHalfUp(posX), roundHalfUp(tops[row]), roundHalfUp(width), roundHalfUp(bottom - tops[row])];
        }
      }
    }
    // Pour le configurateur : la grille de la page affichee (haut des rangees, colonnes)
    const grid = { tops: {}, areaX: areaX, areaY: areaY, area: [areaX, areaY, areaW, areaH], columnW: columnW, gapX: gapX, gapY: gapY,
                   buttonH: buttonH, columns: columns, subcells: SUBCELLS };
    if (pages.length) {
      let y = null;
      for (const row of pages[page]) {
        grid.tops[row] = row in tops ? tops[row] : (y === null ? areaY : y);
        y = grid.tops[row] + buttonH + gapY;
      }
    }
    return { rects: rects, page: page, pages: pages.length, rows: count, cells: cells, grid: grid, members: flowing };
  }

  const api = { merge: merge, roundHalfUp: roundHalfUp, roundHalfEven: roundHalfEven, Units: Units, layout: layout, ANCHORS: ANCHORS,
                LAYOUT_DEFAULTS: LAYOUT_DEFAULTS, GAP_DEFAULT: GAP_DEFAULT, isDict: isDict, zonesOf: zonesOf, SUBCELLS: SUBCELLS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.MenusLayout = api;
})(typeof window !== 'undefined' ? window : globalThis);
