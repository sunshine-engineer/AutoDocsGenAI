(() => {
  const toggle = document.querySelector('.reader-menu-toggle');
  const navigation = document.querySelector('.wy-nav-side');
  if (toggle && navigation) {
    navigation.id = 'reader-navigation';
    navigation.setAttribute('aria-label', 'Documentation navigation');
    const sync = () => toggle.setAttribute('aria-expanded', String(navigation.classList.contains('shift')));
    new MutationObserver(sync).observe(navigation, { attributes: true, attributeFilter: ['class'] });
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
  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    let count = 0;
    let releases = 0;
    cards.forEach(card => {
      const visible = card.dataset.search.includes(query);
      card.hidden = !visible;
      if (visible) { count++; releases += Number(card.dataset.releases); }
    });
    status.textContent = `${count} packages · ${releases} reference releases`;
    empty.hidden = count !== 0;
  });
})();
