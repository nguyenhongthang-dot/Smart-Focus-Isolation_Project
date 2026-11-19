/* Bộ icon SVG dùng chung */
(function () {
  "use strict";
  window.SFIT = window.SFIT || {};

  /* ---------- Icons ---------- */
  var STROKE =
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"';
  var ICONS = {
    home: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5 2 11.5h3V21h5.5v-6h3v6H19v-9.5h3z"/></svg>',
    hist:
      "<svg " +
      STROKE +
      '><path d="M3.5 12a8.5 8.5 0 1 0 2.8-6.3L3.5 8.5"/><path d="M3.5 3.5v5h5"/><path d="M12 7.5V12l3 2"/></svg>',
    gear:
      "<svg " +
      STROKE +
      '><circle cx="12" cy="12" r="5.2" stroke-width="3"/><circle cx="12" cy="12" r="8.6" stroke-width="3.4" stroke-dasharray="3.4 3.4"/></svg>',
    bulb:
      "<svg " +
      STROKE +
      '><path d="M9 18h6M10 21.5h4M12 2.5a6.5 6.5 0 0 0-4 11.6c.8.7 1.2 1.6 1.2 2.5h5.6c0-.9.4-1.8 1.2-2.5A6.5 6.5 0 0 0 12 2.5z"/><path d="M12 .3v.4M3.3 4l.3.3M20.7 4l-.3.3M1 10h.5M22.5 10H23" stroke-width="1.6"/></svg>',
    vol: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><g transform="translate(24 0) scale(-1 1)"><path d="M3 9.5v5h4l5 4.5V5L7 9.5z" fill="currentColor"/><path d="M15.5 9a4 4 0 0 1 0 6M18.5 6a8 8 0 0 1 0 12"/></g></svg>',
    fire: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c1 3.5 5 5.5 5 10.5A5 5 0 0 1 12 22a5 5 0 0 1-5-5c0-2 1-3.5 2-4.5 0 1.5.6 2.2 1.4 2.5C10 12 10.5 6 12 2z"/></svg>',
    hg:
      "<svg " +
      STROKE.replace('stroke-width="2.2"', 'stroke-width="1.6"') +
      '><path d="M7 3h10M7 21h10M8 3c0 5 8 6 8 9s-8 4-8 9M16 3c0 5-8 6-8 9s8 4 8 9"/></svg>',
    rs:
      "<svg " +
      STROKE.replace('stroke-width="2.2"', 'stroke-width="2.4"') +
      '><path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20 3v5h-5"/></svg>',
  };

  window.SFIT.ICONS = ICONS;
})();
