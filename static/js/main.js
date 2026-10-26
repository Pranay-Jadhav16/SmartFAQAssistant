/**
 * Smart FAQ Assistant - Unified Single-Page Application (SPA) Controller
 * Handles Hash Routing (#home, #chat, #faqs, #categories, #about, #admin),
 * Navigation Highlighting, Topbar Breadcrumb, Theme Management,
 * Mobile Sidebar Drawer, Home Search forwarding, FAQ Live Filtering,
 * and Session Recent Questions.
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSidebar();
  initSpaNavigation();
  initHomeInteractions();
  initFaqDirectory();
  initRecentSessionQueries();
  initAlerts();
});

// ---------------------------------------------------------------------------
// 1. Theme Management (Light / Dark Mode)
// ---------------------------------------------------------------------------
function initTheme() {
  const themeToggle = document.getElementById('theme-toggle');
  const storedTheme = localStorage.getItem('sfaq_theme') || 
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  applyTheme(storedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      localStorage.setItem('sfaq_theme', newTheme);
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) {
    if (theme === 'dark') {
      themeIcon.innerHTML = `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>`;
    } else {
      themeIcon.innerHTML = `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>`;
    }
  }
}

// ---------------------------------------------------------------------------
// 2. Responsive Sidebar Drawer (Desktop & Mobile)
// ---------------------------------------------------------------------------
function initSidebar() {
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  const closeBtn = document.getElementById('sidebar-close-btn');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  window.closeAppSidebar = closeSidebar;
}

// ---------------------------------------------------------------------------
// 3. Single-Page Application (SPA) Section Routing
// ---------------------------------------------------------------------------
const VALID_SECTIONS = ['home', 'chat', 'faqs', 'categories', 'about', 'admin'];

const SECTION_TITLES = {
  home: 'Home Dashboard',
  chat: 'AI Chatbot Assistant',
  faqs: 'FAQ Knowledge Base',
  categories: 'Campus Departments',
  about: 'About Project & Architecture',
  admin: 'Administrator Portal'
};

function initSpaNavigation() {
  // Check if we are on the SPA root page
  const spaSections = document.querySelectorAll('.spa-section');
  if (spaSections.length === 0) return; // Not on SPA page

  // Handle Initial Route from URL Hash
  function handleHashChange() {
    let hash = window.location.hash.replace('#', '').trim().toLowerCase();
    if (!VALID_SECTIONS.includes(hash)) {
      hash = 'home';
    }
    navigateToSection(hash, false);
  }

  window.addEventListener('hashchange', handleHashChange);

  // Global click interception for section navigation links
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[data-section], a[href^="#"], a[href*="/#"]');
    if (!link) return;

    // Check if the link targets one of our SPA sections
    let sectionId = link.getAttribute('data-section');
    if (!sectionId) {
      const href = link.getAttribute('href') || '';
      const hashIndex = href.indexOf('#');
      if (hashIndex !== -1) {
        sectionId = href.substring(hashIndex + 1).toLowerCase();
      }
    }

    if (sectionId && VALID_SECTIONS.includes(sectionId)) {
      e.preventDefault();
      navigateToSection(sectionId, true);
    }
  });

  // Expose globally for buttons and handlers
  window.navigateToSection = function(sectionId, updateHash = true) {
    if (!VALID_SECTIONS.includes(sectionId)) {
      sectionId = 'home';
    }

    // Update active section visibility
    document.querySelectorAll('.spa-section').forEach(sec => {
      sec.classList.remove('active');
    });

    const targetSection = document.getElementById(`section-${sectionId}`);
    if (targetSection) {
      targetSection.classList.add('active');
    }

    // Update active sidebar nav link
    document.querySelectorAll('.sidebar-nav .nav-link').forEach(nav => {
      if (nav.getAttribute('data-section') === sectionId) {
        nav.classList.add('active');
      } else {
        nav.classList.remove('active');
      }
    });

    // Update Topbar Section Title Breadcrumb
    const topbarTitle = document.getElementById('topbar-section-title');
    if (topbarTitle) {
      topbarTitle.textContent = SECTION_TITLES[sectionId] || 'Home';
    }

    // Update URL hash without causing a page jump
    if (updateHash && window.location.hash !== `#${sectionId}`) {
      history.pushState(null, '', `#${sectionId}`);
    }

    // Close mobile sidebar if open
    if (window.closeAppSidebar) {
      window.closeAppSidebar();
    }

    // Scroll to top of content wrapper smoothly
    const contentWrapper = document.getElementById('app-content-wrapper');
    if (contentWrapper) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // If navigating to Chatbot, focus the input field
    if (sectionId === 'chat') {
      setTimeout(() => {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) chatInput.focus();
      }, 150);
    }
  };

  // Run on initial page load
  handleHashChange();
}

// ---------------------------------------------------------------------------
// 4. Home Dashboard Interactions (Quick Search, Trending, Categories)
// ---------------------------------------------------------------------------
function initHomeInteractions() {
  // 1. Home Search Bar Submission
  const homeSearchForm = document.getElementById('home-search-form');
  const homeSearchInput = document.getElementById('home-search-input');

  if (homeSearchForm && homeSearchInput) {
    homeSearchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = homeSearchInput.value.trim();
      if (!query) return;

      homeSearchInput.value = '';
      window.navigateToSection('chat');

      // Send question directly into Chatbot
      if (window.sendChatMessage) {
        window.sendChatMessage(query);
      }
    });
  }

  // 2. Trending Questions Clicks
  document.querySelectorAll('[data-ask-question]').forEach(btn => {
    btn.addEventListener('click', () => {
      const qText = btn.getAttribute('data-ask-question');
      if (qText) {
        window.navigateToSection('chat');
        if (window.sendChatMessage) {
          window.sendChatMessage(qText);
        }
      }
    });
  });

  // 3. Category Card "Chat in [Category]" Action
  document.querySelectorAll('.btn-category-chat').forEach(btn => {
    btn.addEventListener('click', () => {
      const cat = btn.getAttribute('data-category');
      window.navigateToSection('chat');
      if (window.setChatCategory) {
        window.setChatCategory(cat);
      }
    });
  });

  // 4. Category Card "Browse [Category]" Action
  document.querySelectorAll('.btn-category-browse').forEach(btn => {
    btn.addEventListener('click', () => {
      const cat = btn.getAttribute('data-category');
      window.navigateToSection('faqs');
      if (window.filterFaqByCategory) {
        window.filterFaqByCategory(cat);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// 5. FAQ Directory Live Client-Side Filtering & Accordions
// ---------------------------------------------------------------------------
function initFaqDirectory() {
  const searchInput = document.getElementById('faq-search-input');
  const clearBtn = document.getElementById('faq-search-clear-btn');
  const categoryTabs = document.querySelectorAll('#faq-category-tabs .faq-tab');
  const items = document.querySelectorAll('#faq-list-container .faq-accordion-item');
  const countLabel = document.getElementById('faq-count-label');
  const dynamicEmpty = document.getElementById('faq-dynamic-empty');
  const askAiFallbackBtn = document.getElementById('ask-ai-fallback-btn');

  let activeCategory = '';

  function applyFaqFilters() {
    const query = (searchInput ? searchInput.value.toLowerCase().trim() : '');
    let visibleCount = 0;

    items.forEach(item => {
      const itemCat = item.getAttribute('data-category') || '';
      const itemText = item.getAttribute('data-text') || '';

      const matchCat = !activeCategory || itemCat === activeCategory;
      const matchQuery = !query || itemText.includes(query);

      if (matchCat && matchQuery) {
        item.style.display = 'block';
        visibleCount++;
      } else {
        item.style.display = 'none';
      }
    });

    if (countLabel) {
      countLabel.textContent = `Showing ${visibleCount} question(s)`;
    }

    if (dynamicEmpty) {
      dynamicEmpty.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', applyFaqFilters);
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      activeCategory = '';
      categoryTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-category') === ''));
      applyFaqFilters();
    });
  }

  categoryTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      categoryTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeCategory = tab.getAttribute('data-category') || '';
      applyFaqFilters();
    });
  });

  // Global helper for filtering from external buttons (e.g. from Categories section)
  window.filterFaqByCategory = function(cat) {
    activeCategory = cat || '';
    categoryTabs.forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-category') === activeCategory);
    });
    applyFaqFilters();
  };

  // FAQ Accordion Card Toggle
  document.querySelectorAll('.faq-header').forEach(header => {
    header.addEventListener('click', () => {
      const item = header.closest('.faq-accordion-item');
      if (item) item.classList.toggle('open');
    });
  });

  // Copy FAQ Answer Button
  document.querySelectorAll('.btn-copy-faq').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const text = btn.getAttribute('data-answer');
      if (text) {
        navigator.clipboard.writeText(text).then(() => {
          const original = btn.innerHTML;
          btn.innerHTML = '✓ Copied!';
          btn.style.color = 'var(--success-solid)';
          setTimeout(() => {
            btn.innerHTML = original;
            btn.style.color = '';
          }, 2000);
        });
      }
    });
  });

  // "Test with AI Assistant" Button in FAQ Cards
  document.querySelectorAll('.btn-test-ai').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const question = btn.getAttribute('data-question');
      const category = btn.getAttribute('data-category') || '';
      if (question) {
        window.navigateToSection('chat');
        if (window.sendChatMessage) {
          window.sendChatMessage(question, category);
        }
      }
    });
  });

  // "Ask AI Assistant" Button in Empty State
  if (askAiFallbackBtn) {
    askAiFallbackBtn.addEventListener('click', () => {
      const query = searchInput ? searchInput.value.trim() : '';
      window.navigateToSection('chat');
      if (query && window.sendChatMessage) {
        window.sendChatMessage(query);
      }
    });
  }
}

// ---------------------------------------------------------------------------
// 6. Recent Session Queries (Persistence in sessionStorage)
// ---------------------------------------------------------------------------
function initRecentSessionQueries() {
  renderRecentQueries();

  const clearBtn = document.getElementById('clear-session-history-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      sessionStorage.removeItem('sfaq_recent_queries');
      renderRecentQueries();
    });
  }
}

function getStoredRecentQueries() {
  try {
    const raw = sessionStorage.getItem('sfaq_recent_queries');
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

window.addSessionRecentQuery = function(query) {
  if (!query || query.trim().length === 0) return;
  const cleanQ = query.trim();
  let list = getStoredRecentQueries();

  // Deduplicate and move to top
  list = list.filter(q => q.toLowerCase() !== cleanQ.toLowerCase());
  list.unshift(cleanQ);

  // Keep up to 8 recent questions
  if (list.length > 8) list = list.slice(0, 8);

  try {
    sessionStorage.setItem('sfaq_recent_queries', JSON.stringify(list));
  } catch (e) {}

  renderRecentQueries();
};

function renderRecentQueries() {
  const container = document.getElementById('home-recent-list');
  const clearBtn = document.getElementById('clear-session-history-btn');
  if (!container) return;

  const list = getStoredRecentQueries();

  if (list.length === 0) {
    container.innerHTML = `
      <div class="recent-empty-prompt">
        <span>💡 No questions asked yet in this session. Try searching above or pick a suggested question!</span>
      </div>
    `;
    if (clearBtn) clearBtn.style.display = 'none';
    return;
  }

  if (clearBtn) clearBtn.style.display = 'inline-block';

  container.innerHTML = '';
  list.forEach(q => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'recent-query-chip';
    chip.innerHTML = `<span>💬</span> <span>${escapeHtml(q)}</span>`;
    chip.addEventListener('click', () => {
      window.navigateToSection('chat');
      if (window.sendChatMessage) {
        window.sendChatMessage(q);
      }
    });
    container.appendChild(chip);
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// 7. Flash Notification Dismissal
// ---------------------------------------------------------------------------
function initAlerts() {
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 250);
      }
    });
  });
}
