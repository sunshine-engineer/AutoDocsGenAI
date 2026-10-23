/*
File: website/assets/catalog.js
Purpose: Filter package/version cards and show an accessible empty-state message.
Maintainer: sunshine-engineer
Modified: 2026-10-23
*/
/**
 * Initialize accessible navigation state and package filtering after script load.
 * @returns {void} Installs event listeners only when their target elements exist.
 */
(() => {
  const toggle = document.querySelector('.reader-menu-toggle');
  const navigation = document.querySelector('.wy-nav-side');
  if (toggle && navigation) {
    navigation.id = 'reader-navigation';
    navigation.setAttribute('aria-label', 'Documentation navigation');
    /**
     * Reflect theme navigation state in the toggle's accessibility attributes.
     * @returns {void}
     */
    const sync = () => {
      toggle.setAttribute('aria-expanded', String(navigation.classList.contains('shift')));
    };
    new MutationObserver(sync).observe(navigation, {
      attributes: true,
      attributeFilter: ['class'],
    });
    // KeyboardEvent handler: close expanded navigation on Escape and restore focus.
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && navigation.classList.contains('shift')) {
        toggle.click();
        toggle.focus();
      }
    });
  }

  const input = document.getElementById('package-filter');
  if (!input) return;
  const cards = [...document.querySelectorAll('.package-card')];
  const status = document.getElementById('catalog-count');
  const empty = document.getElementById('catalog-empty');
  // Recompute visible package/release counts for the current search text.
  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    let count = 0;
    let releases = 0;
    // HTMLElement callback: show matching cards and count their reference releases.
    cards.forEach(card => {
      const visible = card.dataset.search.includes(query);
      card.hidden = !visible;
      if (visible) {
        count++;
        releases += Number(card.dataset.releases);
      }
    });
    status.textContent = `${count} packages · ${releases} reference releases`;
    empty.hidden = count !== 0;
  });
})();
