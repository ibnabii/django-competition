function scrollToAnchorFromHash(extraOffset = 0) {
  if (window.location.hash) {
    const anchor = window.location.hash.substring(1);
    const el = document.getElementById(anchor);
    if (el) {
      const y = el.getBoundingClientRect().top + window.pageYOffset - extraOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  }
}

// Run on initial load (in case page opened with a hash)
document.addEventListener('DOMContentLoaded', function() {
  // Use a timeout to ensure layout is settled
  setTimeout(function() {
    // Adjust offset if you have a sticky header (change 80 to match yours)
    scrollToAnchorFromHash(120);
  }, 100);
});

// Run when hash changes (e.g., from clicking link in SVG)
window.addEventListener('hashchange', function() {
  // Adjust offset if you have a sticky header (change 80 to match yours)
  scrollToAnchorFromHash(120);
});