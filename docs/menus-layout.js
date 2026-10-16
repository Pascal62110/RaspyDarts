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

  // cmenustyle.layout : rectangles [x, y, w, h] des boutons (index depuis 1), page, pages
  function layout(menu, buttons, screenSize, resolution, selected) {
    if (selected === undefined) selected = 1;
    const units = new Units(screenSize, resolution);
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

    const flowing = [];
    buttons.forEach((button, i) => { if (!button.place) flowing.push(i + 1); });
    let buttonH;
    if (size.height !== null && size.height !== undefined) {
      buttonH = units.length(size.height, 'y');
    } else {
      // Tuiles carrees : aussi grandes que leurs rangees tiennent (3 rangees au plus, puis pages)
      const needed = Math.max(1, Math.min(3, Math.ceil(flowing.length / columns)));
      buttonW = buttonH = Math.min(buttonW, (areaH - (needed - 1) * gapY) / needed);
    }
    const rows = [];
    flowing.forEach((index, position) => {
      if (position % columns === 0) rows.push([]);
      rows[rows.length - 1].push(index);
    });

    const spaceOf = (row) => row.reduce((sum, index) => sum + num(buttons[index - 1].space_before, 0), 0) * buttonH;
    let pages = [], pageRows = [], used = 0;
    for (const row of rows) {
      const space = spaceOf(row);
      let height = space + buttonH + (pageRows.length ? gapY : 0);
      if (pageRows.length && used + height > areaH + 0.5) {
        pages.push(pageRows);
        pageRows = [];
        used = 0;
        height = space + buttonH;
      }
      pageRows.push(row);
      used += height;
    }
    if (pageRows.length) pages.push(pageRows);
    const scroll = String(menu.overflow || 'pages') === 'scroll';
    if (scroll) pages = pages.length ? [[].concat(...pages)] : [];

    let page = 0;
    pages.forEach((rowsOfPage, number) => {
      if (rowsOfPage.some(row => row.includes(selected))) page = number;
    });

    const rects = {};
    if (pages.length) {
      const rowsOfPage = pages[page];
      const heights = rowsOfPage.map((row, position) => spaceOf(row) + (position ? gapY : 0));
      const blockH = heights.reduce((a, b) => a + b, 0) + rowsOfPage.length * buttonH;
      let top = areaY + (String(menu.align || 'center') === 'center' ? (areaH - blockH) / 2 : 0);
      if (scroll && blockH > areaH) {
        const rowOf = rowsOfPage.findIndex(row => row.includes(selected));
        const selectedBottom = heights.slice(0, rowOf + 1).reduce((a, b) => a + b, 0) + (rowOf + 1) * buttonH;
        top = areaY - Math.max(0, selectedBottom - areaH);
      }
      let posY = top;
      rowsOfPage.forEach((row, position) => {
        posY += heights[position];
        const usedW = row.length * columnW + (row.length - 1) * gapX;
        const left = areaX + (areaW - usedW) / 2;
        row.forEach((index, column) => {
          const posX = left + column * (columnW + gapX) + (columnW - buttonW) / 2;
          rects[index] = [roundHalfUp(posX), roundHalfUp(posY), roundHalfUp(buttonW), roundHalfUp(buttonH)];
        });
        posY += buttonH;
      });
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
    return { rects: rects, page: page, pages: pages.length };
  }

  const api = { merge: merge, roundHalfUp: roundHalfUp, roundHalfEven: roundHalfEven, Units: Units, layout: layout, ANCHORS: ANCHORS,
                LAYOUT_DEFAULTS: LAYOUT_DEFAULTS, GAP_DEFAULT: GAP_DEFAULT, isDict: isDict };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.MenusLayout = api;
})(typeof window !== 'undefined' ? window : globalThis);
